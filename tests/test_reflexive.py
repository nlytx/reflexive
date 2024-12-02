import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
logging.basicConfig(level=logging.INFO)

import json
import pandas as pd
import time

import reflexive as rfx

# Create a config with a profile (local credentials) - leave blank for 'default' profile
cfg = rfx.cfg.Config('r3-admin')
# Set default parameters - specify name_prefix, local_path, and date_string for custom options
parameters = cfg.set_parameters()
#print("After set_parameters:",parameters)

# Create a session with AWS using profile - some parameters require AWS session (like account number)
aws = rfx.session.AWS(cfg)
#print("aws parameters:",cfg.get_parameters())

# Set the parameters for S3 - required for comprehend
parameters = cfg.set_s3_parameters(s3_access_point="qut-gibsonap-reflexive",s3_bucket_name="au-edu-qld-qut-gibsonap-reflexive")
#print("After set_s3_parameters:",parameters)

# Set comprehend parameters
parameters = cfg.set_comprehend_parameters(comprehend_service_role_name="AmazonComprehendServiceRole-gibsonap-reflexive")
#print("After set_comprehend_parameters:",parameters)

# Set custom entity recogniser parameters
parameters = cfg.set_comprehend_custom_entity_parameters(reflexive_entity_name="ReflexiveExpressionRecogniser",reflexive_entity_version="v17")
#print("After set_comprehend_custom_entity_parameters:",parameters)

# Display all parameters stored in Config
params_fmt = json.dumps(parameters, indent=2)
#print(params_fmt)

# Create a new S3 client
s3 = rfx.session.S3(aws)
s3_client = s3.client()

# Create a new Comprehend client
comp = rfx.session.Comprehend(aws)
comp_client = comp.client()

# Perform test analysis
test_dict = {"text":["This is a test text. I hope that this will work for some basic analysis. Previously, this has not been as straight forward as I thought. Perhaps this time may be different. With any luck, this will not be a frustrating experience, but I hope that it will just work straight away. I can only hope!"]}
test_series = pd.Series(test_dict['text'])
df = pd.DataFrame.from_dict(test_dict)
#print(df.describe())

nlp = rfx.analyse.Nlp(aws)

# Text length - this is needed for comprehend analytics
df = nlp.text_length(df)
df = nlp.remove_IQR_outliers(df)
#print(df.describe())

# Domain terms
#domain_terms = {"hedge":['hope','perhaps','luck'],"emotion":['hope','frustrating']}
#nlp.add_domain_terms(domain_terms)
#df = nlp.match_domain_terms(df)
#print(df['domain_counts'])

# Ngrams
#top_ngrams = nlp.get_top_ngrams(df['text'],2)
#print(top_ngrams)
#df = nlp.match_top_ngrams(df)
#print(df)

# Comprehend analysis
# results = nlp.comprehend_analysis(comp,df)
# print(results)
# errors = nlp.check_results(results)
# print(errors)
# if errors=={}:
#    print("No errors, so adding results to dataframe")
#    df = nlp.add_results_to_df(results,df)
# print(df)

# df.to_pickle(f"{cfg.local_path}comp_df.pkl")
df = pd.read_pickle(f"{cfg.local_path}comp_df.pkl")

# Comprehend analytics
df = nlp.comprehend_analytics(df)
df.to_csv(f"{cfg.local_path}comp_analytics.csv")
print("DONE!!")

# Reflexive expression analysis
response = nlp.analyse_reflexive_expressions(df,s3,comp)
print(response)
job_id = comp.get_current_job_id()
time.sleep(5)
status = comp.check_job_status()
print(status)
time.sleep(5)
details = comp.get_job_details()
print(details)

while status=="IN_PROGRESS":
    time.sleep(10)
    status = comp.check_job_status()
    print(status)

result = comp.download_and_extract(s3)
print(result)


