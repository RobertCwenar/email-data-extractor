# Job Data Extractor

This project is an email parsing pipeline designed to process and analyze incoming job offers. It focuses on extracting structured data from emails received from job portals such as Pracuj.pl, RocketJobs, TheProtocolIT, LinkedIn, and justjoin IT.
The main goal of the project is to automate the process of monitoring job offers and reduce the manual work required to search for jobs and register relevant information. The collected data is validated using Python and stored in an SQLite database for further analysis.

The collected information includes job title, company, salary, location, source, job level, category, and other relevant job offer information.

The project is designed to help answer questions such as:
'''

1. Recruitment activity
   • Which companies are actively recruiting for the positions you are interested in?
2. Job market demand
   • Which job positions are most frequently advertised?
3. Compensation
   • How much do different positions pay across different companies?
4. Career level
   • How does salary vary between different experience levels?
5. Job categories
   • How does salary vary between different job categories?
6. Salary estimation
   • How do estimated salary ranges compare with salary information provided in job offers?
7. Skills
   • Which skills are most frequently required for specific positions?
8. Salary and skills
   • Which skills are associated with higher salary ranges?
9. Companies
   • Which companies offer the highest salaries for specific positions?
10. Location
   • How does salary vary between different job locations?
   '''
   As the database grows, the collected data can be used to identify trends and changes in the job market over time. It can also be used to create reports and dashboards for further analysis.

An important part of the project is the SalaryEstimator, which estimates salary ranges for different positions and experience levels. The salary can be calculated using several sources, including salary information from job offers, historical salary data, and predefined rules stored in a JSON configuration file. More information about the salary estimation process is available in the technical documentation.
The project will be continuously developed and updated in the future as new requirements and analytical possibilities emerge.
