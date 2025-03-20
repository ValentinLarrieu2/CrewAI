from src.reporting_flow.llm_config import llm
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
import os
from src.reporting_flow.config import REPORTING_FLOW_INPUT_VARIABLES

# Uncomment the following line to use an example of a custom tool
# from reporting_content_writer.tools.custom_tool import MyCustomTool

# Check our tools documentations for more information on how to use them
# from crewai_tools import SerperDevTool

@CrewBase
class ReportingContentWriterCrew():
	input_variables = REPORTING_FLOW_INPUT_VARIABLES
	"""ReportingContentWriter crew"""

	def __init__(self):
		# Output folders are now managed by main.py
		pass

	@agent
	def content_manager(self) -> Agent:
		"""Creates a manager agent to oversee the content creation process"""
		return Agent(
			config=self.agents_config['content_manager'],
			llm=llm,
			verbose=True,
			allow_delegation=True,
			tools=[],  # Manager doesn't need tools, just delegates
		)

	@agent
	def content_writer(self) -> Agent:
		return Agent(
			config=self.agents_config['content_writer'],
			llm=llm,
			verbose=True,
			allow_delegation=False,
			tools=[],
		)

	@agent
	def editor(self) -> Agent:
		return Agent(
			config=self.agents_config['editor'],
			llm=llm,
			verbose=True,
			allow_delegation=False,
			tools=[],
		)

	@agent
	def quality_reviewer(self) -> Agent:
		return Agent(
			config=self.agents_config['quality_reviewer'],
			llm=llm,
			verbose=True,
			allow_delegation=False,
			tools=[],
		)

	@task
	def writing_task(self) -> Task:
		return Task(
			config=self.tasks_config['writing_task'],
			async_execution=False,
		)

	@task
	def editing_task(self) -> Task:
		# Output file path is no longer needed here as sections are managed by main.py
		return Task(
			config=self.tasks_config['editing_task'],
			async_execution=False,
		)

	@task
	def quality_review_task(self) -> Task:
		return Task(
			config=self.tasks_config['quality_review_task'],
			async_execution=True,
		)

	@crew
	def crew(self) -> Crew:
		"""Creates the ReportingContentWriter crew with hierarchical process"""
		return Crew(
			agents=[self.content_writer(), self.editor(), self.quality_reviewer()],
			tasks=self.tasks,
			manager_agent=self.content_manager(),  # Set the content manager as the manager agent
			process=Process.hierarchical,
			verbose=True,
			planning=True,  # Enable planning for better coordination
		) 