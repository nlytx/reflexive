
import boto3
import time
import tarfile
import json

from reflexive import cfg
import reflexive as rfx

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AWS:
    
    config = None
    aws_session = None

    def __init__(self,config:cfg.Config):
        # on initialisation create a new session with provided profile (or with default profile)
        #logger.error(config.get_parameters())
        if config==None:
            config = cfg.Config()
        self.config = config
        self.new_session()
        
    def get_parameters(self):
        return self.__dict__
        
    def new_session(self):
        logger.info("In new_session")
        try:
            self.aws_session = boto3.Session(profile_name=self.config.aws_profile)
            self.config.aws_region = self.aws_session.region_name
            self.config.aws_access_key = self.aws_session.get_credentials().access_key
            logger.info("Created new AWS session in region %s for profile: %s",self.config.aws_region,self.config.aws_profile)
            
        except Exception as e:
            logger.error("Unable to create an AWS session: %s",repr(e))
            
        try:
            self.config.aws_account_number = self.aws_session.client('sts').get_caller_identity().get('Account')
            logger.info("Retrieved account number from AWS")
        except Exception as e:
            logger.error("Unable to retrieve account number from AWS: %s",repr(e))
        
        return self.aws_session
            
            
class S3:
    
    aws = None
    config = None
    __s3_client = None
    
    def __init__(self,aws:AWS):
        self.aws = aws
        self.config = self.aws.config

        # create client
        try:
            logger.debug(f"Region:{self.aws.aws_session.region_name}")
            self.__s3_client = aws.aws_session.client(service_name='s3')
        except Exception as err:
            logger.error("Unable to create S3 client: ",err)
    
    # Return the S3 client
    def client(self):
        return self.__s3_client
    
     # Function to upload reflections to S3
    def upload_docs(self,text_series):

        files_folder = f"{self.config.prefix}files{self.config.postfix}"

        s3 = self.__s3_client
        s3ap = self.config.s3_accesspoint_arn
        logger.debug(f"ACCESS POINT: {s3ap}")

        logger.info(f"Uploading {len(text_series)} reflections to S3 ({files_folder})...")
        logger.debug(f"({s3ap}/{files_folder})")
        for idx in text_series.index:
            file_name = f"{self.config.prefix}{idx}.txt"
            file_body = text_series.iloc[idx]
            logger.info(f"Uploading {file_name}")
            #print(file_body)
            response = s3.put_object(Body=file_body,Bucket=s3ap,Key=f"{files_folder}/{file_name}")
            if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                logger.error("------------------------------------------------------------")
                logger.error(f"ERROR: There was a problem with {file_name}")
                logger.error(response)
                logger.error("------------------------------------------------------------")
            else:
                logger.info('Success')
        logger.info("Finished uploading reflections to S3.")
        return response
    
    # download and save results
    def results_download_save_extract(self,s3Uri,local_file_path):
        s3 = self.__s3_client
        output_key = s3Uri.split(self.config.s3_bucket_name)[1]
        # download from S3 to local path
        with open(f"{local_file_path}.tar.gz",'wb') as output_data:
            s3.download_fileobj(self.config.s3_bucket_name,output_key[1:],output_data)

        # extract the files from tar archive
        files = list()
        with tarfile.open(f"{local_file_path}.tar.gz", "r:gz") as tf:
            for member in tf.getmembers():
                f = tf.extractfile(member)
                if f is not None:
                    content = f.read()
                    files.append(content)
        #print("Number of files:",len(files))
        # extract results and save and return
        raw_results = files[0].decode("utf-8").split('\n')
        raw_results.pop() # pop last item off as empty entry due to final \n
        json_results = json.dumps(raw_results)
        with open(f"{local_file_path}.json","w") as fp:
            fp.write(json_results)
        return json_results


class Comprehend:
    
    aws = None
    config = None
    __comp_client = None
    
    def __init__(self,aws:AWS):
        self.aws = aws
        self.config = self.aws.config
    
        # create client
        try:
            logger.debug(f"Region:{self.aws.aws_session.region_name}")
            self.__comp_client = self.aws.aws_session.client(service_name='comprehend')
        except Exception as err:
            logger.error("Unable to create Comprehend client: ",err)
                
    def client(self):
        return self.__comp_client
        
    # Use AWS comprehend to get bulk key phrases from single batch of chunked text
    def get_single_batch_analysis(self,index,chunk):
        comp_client = self.client()
        results = {}
        print("Analysing chunk",index)
        print(" . key_phrase")
        kpresult = comp_client.batch_detect_key_phrases(TextList=chunk,LanguageCode='en')
        results['KeyPhraseResults'] = kpresult
        #key_phrase_results.append(kpresult)
        time.sleep(2)
        print(" . sentiment")
        senresult = comp_client.batch_detect_sentiment(TextList=chunk,LanguageCode='en')
        results['SentimentResults'] = senresult
        #sentiment_results.append(senresult)
        time.sleep(2)
        print(" . targeted_sentiment")
        tsenresult = comp_client.batch_detect_targeted_sentiment(TextList=chunk,LanguageCode='en')
        results['TargetedSentimentResults'] = tsenresult
        #target_sent_results.append(tsenresult)
        time.sleep(2)
        print(" . syntax")
        synresult = comp_client.batch_detect_syntax(TextList=chunk,LanguageCode='en')
        results['SyntaxResults'] = synresult
        #syntax_results.append(synresult)       
        time.sleep(2)
        return results


    # Use AWS comprehend to get bulk key phrases from chunked text
    def get_multiple_batch_analysis(self,chunked_text):
        chunk_results = {}
        for key in self.config.analysis_types.keys():
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
    
# #### CUSTOM ENTITY

    def submit_custom_entity_job(self,job_name): #access_role_arn,entity_recogniser_arn):
        job_str = f"{self.config.prefix}{job_name}{self.config.postfix}"
        
        response = self.__comp_client.start_entities_detection_job(
            InputDataConfig={
                'S3Uri': self.config.s3_input_uri,
                'InputFormat': 'ONE_DOC_PER_FILE'
            },
            OutputDataConfig={
                'S3Uri': self.config.s3_output_uri
            },
            DataAccessRoleArn=self.config.comprehend_access_role_arn,
            JobName=job_str,
            EntityRecognizerArn=self.config.reflexive_entity_arn,
            LanguageCode='en'
        )
        self.job_id = response['JobId']
        self.check_job_status() # force the creation of __job_properties
        return response
    
    def get_current_job_id(self):
        return self.job_id
    
            # Check job status
    def check_job_status(self):
        job_status = self.__comp_client.describe_entities_detection_job(
            JobId=self.job_id
        )
        self.__job_properties = job_status['EntitiesDetectionJobProperties'] 
        return self.__job_properties['JobStatus']

    def get_job_details(self):
        return self.__job_properties
    
        #checked
    def download_and_extract(self,s3):
        local_output_dir = f"{self.config.local_path}{self.config.prefix}output{self.config.postfix}"
        job_details = self.get_job_details()
        s3Uri = job_details['OutputDataConfig']['S3Uri']
        return s3.results_download_save_extract(s3Uri,local_output_dir)
       