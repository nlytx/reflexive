#

import logging,coloredlogs
import pandas as pd
import json

from reflexive.common.parameters import Parameters
from reflexive.common.local import Local
from reflexive.common.util import Util
from reflexive.aws_connect.s3 import S3
from reflexive.aws_connect.comprehend import Comprehend


coloredlogs.install(level='INFO')

class ReflexiveExpressions:
    
    logger = logging.getLogger(__name__)
    
    def __init__(self,parameters:Parameters,aws_s3:S3,local:Local,comprehend:Comprehend):
        #print(parameters)
        self.__params = parameters
        self.__parameters = parameters.all_parameters()
        self.logger.debug(f"Parameters: {self.__parameters}")
        self.prefix = self.__parameters['prefix']
        self.postfix = self.__parameters['postfix']
        self.local_path = self.__parameters['local_path']
        self.__s3 = aws_s3
        self.__local = local
        self.__comprehend = comprehend

        
    ######## REFLEXIVE EXPRESSION ANALYSIS FUNCTIONS

    def analyse_reflexive_expressions(self,df): #,s3_bucket_name,access_role_arn,entity_recogniser_arn):
        #self.__bucket_name = s3_bucket_name
        text = df.text.replace('\r\n','\n') # Comprehend treats \r\n as one character
        # Upload reflections to S3 for analysis
        self.__s3.upload_docs(text)
        
        # Save a copy of reflections locally for offline analysis
        self.__local.save_docs(text)

        # Submit the job
        return self.__comprehend.submit_custom_entity_job("reflexive_expressions_analysis") #submitReflexiveExpressionsJob(access_role_arn, entity_recogniser_arn)
    
    def check_job_status(self):
        return self.__comprehend.check_job_status()
    
    def get_job_details(self):
        return self.__comprehend.get_job_details()

    def download_and_extract(self):
        local_output_dir = f"{self.local_path}{self.prefix}output{self.postfix}"
        job_details = self.get_job_details()
        s3Uri = job_details['OutputDataConfig']['S3Uri']
        return self.__s3.results_download_save_extract(s3Uri,local_output_dir)

    def extractAnalysisFromResults(self,results):
        analysis_output = dict()
        for result in results:
            j = json.loads(result)
            #print(j)
            idx = j["File"].split('_')[-1].split('.')[0]
            analysis_output[int(idx)] = j["Entities"]
        return analysis_output
    
    def add_to_dataframe(self,df,results):
        # Extract analysis from raw results
        analysis_output = self.extractAnalysisFromResults(results)
        # Add results to dataframe
        results_df = df.copy()
        results_df['reflexiveResults'] = pd.Series(analysis_output)
        return results_df

    def reflexive_analytics(self,df):
        util = Util()
        custom_df = df.copy() 
        # custom_df["text_length"] = df.text.apply(lambda x: len(x))
        # if (len(custom_df)>1):
        #     custom_df["text_scaled"] = util.scale_min_max(custom_df[['text_length']])
        # else:
        #     custom_df["text_scaled"] = 1
        custom_df["reflexive_results"] = df.reflexiveResults
        # The expressions and their reflexive expression labels
        custom_df["reflexive_expressions"] = df.reflexiveResults.apply(self.parse_reflexiveResults)
        # The counts for each labels
        custom_df["reflexive_counts"] = custom_df.reflexive_expressions.apply(util.count_labels)
        # Ratios between reflexive expressions
        custom_df["reflexive_ratio"] = custom_df.reflexive_counts.apply(util.ratios)
        # Ratio vector
        custom_df['ratio_vector'] = custom_df.reflexive_ratio.apply(self.make_ratio_vector)
        # Get the diversity of reflexive types - out of 8 possible types
        custom_df["reflexive_type_diversity"] = custom_df.reflexive_counts.apply(lambda x: len(x)/8)
        # A total of all labels
        custom_df["reflexive_total"] = custom_df.reflexive_counts.apply(util.tuple_values_total)
        # MinMax scale the reflexive_total
        if (len(custom_df)>1):
            custom_df["reflexive_scaled"] = util.scale_min_max(custom_df[['reflexive_total']])
        else:
            custom_df["reflexive_scaled"] = 1
        # Normalise based on text_scaled
        custom_df['reflexive_norm'] = util.normalise_scaled(custom_df,'reflexive_scaled')
        return custom_df


    # Parse reflexive results - include all above threshold
    def parse_reflexiveResults(self,reflexiveResults,threshold=0.5):
        final_refs = list()
        for ref in reflexiveResults:
            if ref['Score'] > threshold:
                final_refs.append((str.lower(ref['Text']),ref['Type']))
        return final_refs
    
        # Function for creating a vector out of reflexive ratio - could be used for others
    def make_ratio_vector(self,ratio_list,ref_codes = ['RR','ER','VR','AR','EP','AF','CN','EV']):
        ratio_dict = dict(ratio_list)
        vec = []
        for rc in ref_codes:
            if rc in ratio_dict.keys():
                vec.append(ratio_dict[rc])
            else:
                vec.append(0)
        return vec