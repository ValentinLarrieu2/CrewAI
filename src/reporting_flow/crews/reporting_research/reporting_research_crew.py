import os
import json
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

# Tools for improved research
from crewai_tools import SerperDevTool

# Optional - if you want to use Tavily as an alternative search
# from tavily import TavilyClient
# from crewai_tools import TavilySearchTool

from pydantic import BaseModel, Field
from typing import List, Optional

# Define the LLM instance at the top level
from src.reporting_flow.llm_config import llm


class Section(BaseModel):
    """A section of the report"""
    title: str
    high_level_goal: str
    why_important: str
    sources: List[str] = Field(description="List of URLs, papers, or other sources")
    content_outline: List[str]
    
    def model_dump_json(self):
        """Convert to JSON string"""
        return json.dumps({
            "title": self.title,
            "high_level_goal": self.high_level_goal,
            "why_important": self.why_important,
            "sources": self.sources,
            "content_outline": self.content_outline
        })

class ReportingPlan(BaseModel):
    """The overall plan for the report"""
    sections: List[Section]
    primary_audience: str = Field(description="The primary audience for this report")
    secondary_audiences: Optional[List[str]] = Field(default=None, description="Other audiences who might find this report useful")
    executive_summary: str = Field(description="A concise summary of the entire report's key findings")
    
    def to_dict(self):
        """Convert to dictionary for easier serialization"""
        return {
            "sections": [s.__dict__ for s in self.sections],
            "primary_audience": self.primary_audience,
            "secondary_audiences": self.secondary_audiences,
            "executive_summary": self.executive_summary
        }
    
    def model_dump_json(self):
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

@CrewBase
class ReportingResearchCrew():
    """ReportingResearch crew with enhanced capabilities for better research, examples, and graphics"""

    def __init__(self):
        # Initialize the SerperDevTool with API key from environment variable
        serper_api_key = os.getenv("SERPER_API_KEY", "").strip()
        if not serper_api_key:
            print("Warning: SERPER_API_KEY not found in environment variables")
        self.search_tool = SerperDevTool(api_key=serper_api_key)

    @agent
    def research_manager(self) -> Agent:
        """Creates a manager agent to oversee the research process"""
        return Agent(
            config=self.agents_config['research_manager'],
            llm=llm,
            verbose=True,
            allow_delegation=True,
            # Configure collaboration properly with correct tool schema
            tools=[],
        )

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'],
            llm=llm,
            verbose=True,
            tools=[self.search_tool],
            allow_delegation=False,  # This agent doesn't delegate, just uses tools
        )

    @agent
    def planner(self) -> Agent:
        return Agent(
            config=self.agents_config['planner'],
            llm=llm,
            verbose=True,
            tools=[],
            allow_delegation=False,  # This agent doesn't delegate
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'],
            async_execution=False,
        )

    @task
    def planning_task(self) -> Task:
        """Define the planning task with direct reference to the ReportingPlan class"""
        return Task(
            config=self.tasks_config['planning_task'],
            output_pydantic=ReportingPlan,
            async_execution=True,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the enhanced ReportingResearch crew with sequential process"""
        return Crew(
            agents=[self.researcher(), self.planner()],
            tasks=self.tasks,
            process=Process.sequential,  # Change to sequential for simplicity and reliability
            verbose=True,
        ) 