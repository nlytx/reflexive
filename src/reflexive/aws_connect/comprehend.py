#


import boto3
import time
import json
import pandas as pd

from reflexive.common.parameters import Parameters
from reflexive.common.util import Util
from reflexive.aws_connect.s3 import S3

import logging
try:
    import coloredlogs
    coloredlogs.install(level='INFO')
except:
    print("Colored logs not available")

class Comprehend:
    
    logger = logging.getLogger(__name__)
    
    def __init__(self,parameters:Parameters):
        #print(parameters)
        self.__parameters = parameters.all_parameters()
        self.logger.debug(f"Parameters: {self.__parameters}")
        self.region = self.__parameters['region']
        self.access_role_arn = self.__parameters['comprehend_access_role_arn']
        self.entity_recogniser_arn = self.__parameters['reflexive_entity_arn']
        self.local_path = self.__parameters['local_path']
        self.prefix = self.__parameters['prefix']
        self.postfix = self.__parameters['postfix']
        self.bucket_name = self.__parameters["bucket_name"]
        self.files_folder = f"{self.prefix}files{self.postfix}"
        self.results_folder = f"{self.prefix}results{self.postfix}"
        self.input_uri = f"s3://{self.bucket_name}/{self.files_folder}/{self.prefix}"
        self.output_uri = f"s3://{self.bucket_name}/{self.results_folder}/"
        self.analysis_types = self.__parameters['analysis_types']
        # create client
        try:
            self.logger.debug(f"Region:{self.region}")
            self.__comp_client = boto3.client(service_name='comprehend',region_name=self.region)
        except Exception as err:
            self.logger.error("Unable to create Comprehend client: ",err)
            
        
    def client(self):
        return self.__comp_client
        
        
#### CUSTOM ENTITY

    def submit_custom_entity_job(self,job_name): #access_role_arn,entity_recogniser_arn):
        job_str = f"{self.prefix}{job_name}{self.postfix}"
    
        response = self.__comp_client.start_entities_detection_job(
            InputDataConfig={
                'S3Uri': self.input_uri,
                'InputFormat': 'ONE_DOC_PER_FILE'
            },
            OutputDataConfig={
                'S3Uri': self.output_uri
            },
            DataAccessRoleArn=self.access_role_arn,
            JobName=job_str,
            EntityRecognizerArn=self.entity_recogniser_arn,
            LanguageCode='en'
        )
        self.job_id = response['JobId']
        return response
    
            # Check job status
    def check_job_status(self):
        job_status = self.__comp_client.describe_entities_detection_job(
            JobId=self.job_id
        )
        self.__job_properties = job_status['EntitiesDetectionJobProperties'] 
        return self.__job_properties['JobStatus']

    def get_job_details(self):
        return self.__job_properties
    
        
    # Use AWS comprehend to get bulk key phrases from single batch of chunked text
    def get_single_batch_analysis(self,index,chunk):
        comprehend = self.client()
        results = {}
        print("Analysing chunk",index)
        print(" . key_phrase")
        kpresult = comprehend.batch_detect_key_phrases(TextList=chunk,LanguageCode='en')
        results['KeyPhraseResults'] = kpresult
        #key_phrase_results.append(kpresult)
        time.sleep(2)
        print(" . sentiment")
        senresult = comprehend.batch_detect_sentiment(TextList=chunk,LanguageCode='en')
        results['SentimentResults'] = senresult
        #sentiment_results.append(senresult)
        time.sleep(2)
        print(" . targeted_sentiment")
        tsenresult = comprehend.batch_detect_targeted_sentiment(TextList=chunk,LanguageCode='en')
        results['TargetedSentimentResults'] = tsenresult
        #target_sent_results.append(tsenresult)
        time.sleep(2)
        print(" . syntax")
        synresult = comprehend.batch_detect_syntax(TextList=chunk,LanguageCode='en')
        results['SyntaxResults'] = synresult
        #syntax_results.append(synresult)       
        time.sleep(2)
        return results


    # Use AWS comprehend to get bulk key phrases from chunked text
    def get_multiple_batch_analysis(self,chunked_text):
        chunk_results = {}
        for key in self.analysis_types.keys():
            chunk_results[key] = []
                
        for idx,chunk in enumerate(chunked_text):
            if len(chunked_text) > 4999:
                print("WARNING: Text too long to analyse - index",idx,"skipped!")
            else:
                try:
                    results = self.get_single_batch_analysis(index=idx,chunk=chunk)
                except(Exception) as error:
                    print("There was an error with index",idx,error)
                finally:
                    if results:
                        for key in results.keys():
                            chunk_results[key].append(results[key])

        return chunk_results

    # Take batched responses and concenate single lists of results, errors, and http responses
    def unbatch_results(self,result_type,results,batch_size=25):
        unbatched_results = {}
        unbatched_errors = {}
        batch_responses = {}
        for idx,batch in enumerate(results):
            #print("Response for batch:",idx)
            batch_responses[idx] = batch['ResponseMetadata']
            result_list = batch['ResultList']
            error_list = batch['ErrorList']
            for r in result_list:
                ridx = idx*batch_size + r['Index']
                rdata = r[result_type]
                unbatched_results[ridx] = rdata
            for e in error_list:
                eidx = e['Index']
                unbatched_errors[eidx] = 'ERROR' + e['ErrorCode'] + ': ' + e['ErrorMessage']
        unbatched = {}
        unbatched['results'] = unbatched_results
        unbatched['errors'] = unbatched_errors
        unbatched['responses'] = batch_responses
        return unbatched



    def check_long_text(self,df):
        # Check for long reflections (too long for batch analysis)
        long_df = df.copy()
        long_df = long_df[long_df.text.str.len()>5000]
        long_df['length'] = long_df.text.str.len()
        return long_df
    
    
    # def extract_result(self,result,batch,batch_params):
    #     match batch:
    #         case "KeyPhraseResults":
    #             extracted = [r['Text'] for r in result if r['Score'] >= batch_params["min_score"]]
    #         case "SentimentResults":
    #             extracted = result
    #         case "TargetedSentimentResults":
    #             extracted = dict()
    #             for r in result:
    #                 for mention in r['Mentions']:
    #                     if (mention['Score'] >= batch_params["min_score"]):
    #                         text = mention['Text']
    #                         key = f"{mention['Type']}_{mention['MentionSentiment']['Sentiment']}"
    #                         if key in extracted.keys():
    #                             extracted[key].add(text)
    #                         else:
    #                             extracted[key] = {text}
    #         case "SyntaxResults":
    #             tags = []
    #             tokens = []
    #             for r in result:
    #                 pos = r['PartOfSpeech']
    #                 tag = pos['Tag']
    #                 if pos['Score'] < batch_params["max_score"]:
    #                     tag = tag+"_?"
    #                 tags.append(tag)
    #                 tokens.append(r['Text'])

    #             extracted = {'tokens':tokens,'tags':tags}
    #         case other:
    #             extracted = []
    #     return extracted







