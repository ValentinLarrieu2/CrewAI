#!/usr/bin/env python
from random import randint
import os
from langtrace_python_sdk import langtrace

from pydantic import BaseModel

from crewai.flow.flow import Flow, listen, start

from .crews.edu_research.edu_research_crew import EduResearchCrew
from .crews.edu_content_writer.edu_content_writer_crew import EduContentWriterCrew

api_key = os.getenv('LANGTRACE_API_KEY')

langtrace.init(api_key=api_key)

class EduFlow(Flow):
    # Extracted input variables
    input_variables = {
        "audience_level": "beginner",
        "topic": "fine-tuning LLMs"
    }

    @start()
    def generate_reseached_content(self):
        return EduResearchCrew().crew().kickoff(self.input_variables).pydantic

    @listen(generate_reseached_content)
    def generate_educational_content(self, plan):
        final_content = []
        for section in plan.sections:
            writer_inputs = self.input_variables.copy()
            writer_inputs['section'] = section.model_dump_json()
            final_content.append(EduContentWriterCrew().crew().kickoff(writer_inputs).raw)
        print(final_content)
        return final_content

    @listen(generate_educational_content)
    def save_to_text(self, content):
        with open('educational_content.txt', 'w') as f:
            for section in content:
                f.write(section)
                f.write('\n\n')

def kickoff():
    edu_flow = EduFlow()
    edu_flow.kickoff()

def plot():
    edu_flow = EduFlow()
    edu_flow.plot()


if __name__ == "__main__":
    kickoff()
