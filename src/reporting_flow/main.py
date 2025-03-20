#!/usr/bin/env python
import os
import asyncio
import json
import re
import sys
import logging
from datetime import datetime
from pydantic import BaseModel

from crewai.flow.flow import Flow, listen, start

from .crews.reporting_research.reporting_research_crew import ReportingResearchCrew
from .crews.reporting_content_writer.reporting_content_writer_crew import ReportingContentWriterCrew
from .config import REPORTING_FLOW_INPUT_VARIABLES

# Create base output directories
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Generate timestamp for this run to create unique folders
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
topic = REPORTING_FLOW_INPUT_VARIABLES.get("topic", "report").replace(" ", "_")
audience = REPORTING_FLOW_INPUT_VARIABLES.get("audience_level", "general").replace(" ", "_")

# Create run-specific directories
run_dir = os.path.join(output_dir, f"{topic}_{audience}_{timestamp}")
report_dir = os.path.join(run_dir, "report")
sections_dir = os.path.join(run_dir, "sections")
debug_dir = os.path.join(run_dir, "debug")

os.makedirs(run_dir, exist_ok=True)
os.makedirs(report_dir, exist_ok=True)
os.makedirs(sections_dir, exist_ok=True)
os.makedirs(debug_dir, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(run_dir, "report_flow.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("report_flow")

#####  To remove if we don't want to use langtrace
from langtrace_python_sdk import langtrace
langtrace_api_key = os.getenv('LANGTRACE_API_KEY')
langtrace.init(api_key=langtrace_api_key)
##### 

# Simplified callback function with correct signature
def task_callback(task):
    """Callback function that gets called after each task is completed"""
    logger.info(f"✅ Task completed: {task.description[:50] if hasattr(task, 'description') else 'Unknown task'}...")
    return task

# Simplified step callback
def step_callback(step_output):
    """Callback function that gets called after each agent step"""
    logger.info(f"🔄 Step: {step_output.get('action', 'Unknown action')}")
    return step_output

class ReportingFlow(Flow):
    input_variables = REPORTING_FLOW_INPUT_VARIABLES

    @start()
    async def generate_researched_content(self):
        """Initial research phase to gather up-to-date information on the topic"""
        logger.info(f"🔍 Starting research on topic: {self.input_variables.get('topic')}")
        
        # Create the research crew with hierarchical process managed by the research manager
        research_crew = ReportingResearchCrew().crew()
        
        # The CrewAI framework handles these callbacks
        result = await research_crew.kickoff_async(self.input_variables)
        
        # Log result details to help with debugging
        logger.info(f"📝 Research result type: {type(result)}")
        logger.info(f"📝 Research result attributes: {dir(result)}")
        
        # Try to access the raw and pydantic attributes
        if hasattr(result, 'raw'):
            logger.info(f"📝 Result raw type: {type(result.raw)}")
            raw_preview = str(result.raw)[:500] + "..." if len(str(result.raw)) > 500 else str(result.raw)
            logger.info(f"📝 Result raw preview: {raw_preview}")
            
            # Save the raw output to a file for inspection
            with open(os.path.join(debug_dir, "research_output_raw.txt"), "w") as f:
                f.write(str(result.raw))
        
        if hasattr(result, 'pydantic'):
            logger.info(f"📝 Result pydantic type: {type(result.pydantic)}")
            if hasattr(result.pydantic, 'sections'):
                logger.info(f"📝 Number of sections in pydantic: {len(result.pydantic.sections)}")
                logger.info(f"📝 Sections: {result.pydantic.sections}")
        
        return result

    @listen(generate_researched_content)
    async def generate_reporting_content(self, plan):
        """Writing phase that creates high-quality content based on research"""
        # Extract sections from the plan, considering different data formats
        sections = []
        
        logger.info(f"📋 Processing plan: {type(plan)}")
        
        # First try the most common attributes
        if hasattr(plan, 'sections'):
            logger.info("📋 Found sections attribute directly on plan")
            sections = plan.sections
        elif hasattr(plan, 'pydantic') and hasattr(plan.pydantic, 'sections'):
            logger.info("📋 Found sections in plan.pydantic")
            sections = plan.pydantic.sections
        elif hasattr(plan, 'raw'):
            logger.info("📋 Attempting to extract sections from raw data")
            # Try to parse from raw JSON
            try:
                # First try direct JSON parsing
                data = json.loads(plan.raw)
                if 'sections' in data:
                    logger.info("📋 Found sections in parsed JSON")
                    sections = data['sections']
            except Exception as e:
                logger.info(f"📋 Error parsing JSON directly: {e}")
                # If that fails, try extracting JSON from possibly multiline text
                json_match = re.search(r'\{.*\}', plan.raw, re.DOTALL)
                if json_match:
                    try:
                        logger.info("📋 Attempting to parse JSON from regex match")
                        data = json.loads(json_match.group(0))
                        if 'sections' in data:
                            logger.info("📋 Found sections in regex-matched JSON")
                            sections = data['sections']
                    except Exception as e:
                        logger.info(f"📋 Error parsing JSON from regex match: {e}")
        
        logger.info(f"📝 Starting content creation for {len(sections)} sections")
        
        # Save the sections to a file for inspection
        with open(os.path.join(debug_dir, "sections_data.json"), "w") as f:
            json.dump(sections if isinstance(sections, list) else [str(sections)], f, indent=2, default=str)
        
        final_content = []
        section_files = []  # Keep track of individual section files
        
        for i, section in enumerate(sections):
            try:
                title = section.get('title', f"Section {i+1}") if isinstance(section, dict) else getattr(section, 'title', f"Section {i+1}")
                
                # Create safe filename from title
                safe_title = re.sub(r'[^\w\-_.]', '_', title)
                
                logger.info(f"📋 Processing section {i+1}: {title}")
                
                # Prepare inputs for the content writer crew
                writer_inputs = self.input_variables.copy()
                
                # Handle different section data formats
                if hasattr(section, 'model_dump_json'):
                    logger.info(f"📋 Section {i+1} has model_dump_json method")
                    writer_inputs['section'] = section.model_dump_json()
                elif isinstance(section, dict):
                    logger.info(f"📋 Section {i+1} is a dictionary")
                    writer_inputs['section'] = json.dumps(section)
                else:
                    logger.info(f"📋 Section {i+1} is type {type(section)}")
                    writer_inputs['section'] = str(section)
                
                # Save the section input for debugging
                with open(os.path.join(debug_dir, f"section_{i+1}_input.json"), "w") as f:
                    json.dump(writer_inputs, f, indent=2, default=str)
                
                # Create the content writer crew with hierarchical process managed by content manager
                content_crew = ReportingContentWriterCrew().crew()
                section_result = await content_crew.kickoff_async(writer_inputs)
                
                logger.info(f"📋 Section {i+1} result type: {type(section_result)}")
                
                # Try multiple ways to extract content from the result
                content = None
                
                # Try common result formats
                if hasattr(section_result, 'raw'):
                    logger.info(f"📋 Section {i+1} has raw attribute with length {len(str(section_result.raw))}")
                    content = section_result.raw
                elif hasattr(section_result, 'output'):
                    logger.info(f"📋 Section {i+1} has output attribute")
                    content = section_result.output
                elif hasattr(section_result, 'result'):
                    logger.info(f"📋 Section {i+1} has result attribute")
                    content = section_result.result
                else:
                    # If all else fails, convert to string
                    logger.info(f"📋 Section {i+1} converted to string")
                    content = str(section_result)
                
                # Check if content is a dictionary and handle appropriately
                if isinstance(content, dict) and 'content' in content:
                    content = content['content']
                
                # Save the section output for debugging
                debug_output_path = os.path.join(debug_dir, f"section_{i+1}_output.txt")
                with open(debug_output_path, "w") as f:
                    f.write(str(content))
                
                # Save the section to its own file in the sections directory
                if content and str(content).strip():
                    section_filename = f"{i+1:02d}_{safe_title}.md"
                    section_path = os.path.join(sections_dir, section_filename)
                    with open(section_path, "w") as f:
                        f.write(str(content))
                    
                    # Add to our tracking lists
                    final_content.append(content)
                    section_files.append(section_path)
                    logger.info(f"✅ Added non-empty content for section {i+1} and saved to {section_path}")
                else:
                    logger.warning(f"⚠️ Section {i+1} produced empty content")
                
                logger.info(f"✅ Completed section {i+1}")
            except Exception as e:
                logger.error(f"Error processing section {i+1}: {e}", exc_info=True)
        
        logger.info(f"📊 Generated {len(final_content)} content sections")
        return {
            "content": final_content,
            "section_files": section_files
        }

    @listen(generate_reporting_content)
    async def save_to_markdown(self, result):
        """Save the final report to a markdown file"""
        content = result["content"] if isinstance(result, dict) and "content" in result else result
        section_files = result.get("section_files", []) if isinstance(result, dict) else []
        
        topic = self.input_variables.get("topic", "report")
        audience_level = self.input_variables.get("audience_level", "general")
        file_name = f"{topic}_{audience_level}.md".replace(" ", "_")
        report_path = os.path.join(report_dir, file_name)
        
        logger.info(f"💾 Saving report with {len(content)} sections to {report_path}")
        logger.info(f"Content types: {[type(item) for item in content]}")
        
        # Debug the content before writing
        for i, section_content in enumerate(content):
            logger.info(f"Section {i+1} content length: {len(str(section_content))}")
            # Save each section to a debug file
            with open(os.path.join(debug_dir, f"final_section_{i+1}.txt"), "w") as f:
                f.write(str(section_content))
        
        # Create a fallback default content if empty
        if not content or all(not str(item).strip() for item in content):
            logger.warning("❌ No content to write! Using fallback content.")
            fallback_content = [
                f"# Report on {topic} for {audience_level} audience\n\n"
                "This report could not be generated properly. Please check the logs."
            ]
            content = fallback_content
        
        # Create a table of contents based on section files
        toc = ["# Table of Contents\n"]
        for i, section_file in enumerate(section_files):
            section_name = os.path.basename(section_file).split("_", 1)[1].replace(".md", "")
            section_rel_path = os.path.relpath(section_file, os.path.dirname(report_path))
            toc.append(f"{i+1}. [{section_name}]({section_rel_path})")
        
        # Write to the final file, including the table of contents
        with open(report_path, "w") as f:
            # Add title and TOC
            f.write(f"# Report: {topic} ({audience_level} audience)\n\n")
            
            # Add table of contents if we have sections
            if section_files:
                f.write("\n".join(toc))
                f.write("\n\n---\n\n")
            
            # Add executive summary if available
            if hasattr(result, 'executive_summary') or (isinstance(result, dict) and 'executive_summary' in result):
                summary = result.executive_summary if hasattr(result, 'executive_summary') else result.get('executive_summary', '')
                f.write(f"## Executive Summary\n\n{summary}\n\n---\n\n")
            
            # Add each section content
            for section in content:
                section_text = str(section).strip()
                if section_text:  # Only write non-empty sections
                    f.write(section_text)
                    f.write("\n\n")
                else:
                    logger.warning("Skipping empty section")
        
        logger.info(f"📊 Report saved to {report_path}")
        
        # Create an index.md file that points to the report
        index_path = os.path.join(run_dir, "index.md")
        with open(index_path, "w") as f:
            f.write(f"# Report: {topic} ({audience_level})\n\n")
            f.write(f"- [Full Report]({os.path.relpath(report_path, run_dir)})\n")
            f.write("## Sections\n\n")
            for i, section_file in enumerate(section_files):
                section_name = os.path.basename(section_file).split("_", 1)[1].replace(".md", "")
                section_rel_path = os.path.relpath(section_file, run_dir)
                f.write(f"{i+1}. [{section_name}]({section_rel_path})\n")
        
        logger.info(f"📄 Index created at {index_path}")
        return {
            "report_path": report_path,
            "index_path": index_path,
            "run_directory": run_dir
        }

async def kickoff_async():
    """Execute the reporting flow asynchronously"""
    reporting_flow = ReportingFlow()
    return await reporting_flow.kickoff_async()

def kickoff():
    """Execute the reporting flow synchronously by running the async version in an event loop"""
    logger.info("🚀 Starting the report generation flow with hierarchical architecture")
    reporting_flow = ReportingFlow()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(reporting_flow.kickoff_async())
        logger.info("✅ Report generation completed successfully")
        logger.info(f"📂 Results are in: {run_dir}")
        if isinstance(result, dict) and "run_directory" in result:
            print(f"Report generated in: {result['run_directory']}")
        return result
    except Exception as e:
        logger.error(f"❌ Error during report generation: {e}", exc_info=True)
        raise
    finally:
        if hasattr(loop, 'close') and not loop.is_closed():
            loop.close()

def plot():
    reporting_flow = ReportingFlow()
    reporting_flow.plot()

if __name__ == "__main__":
    kickoff() 