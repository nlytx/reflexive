# Store the parameters for connecting to AWS

import os
import logging,coloredlogs
from datetime import datetime
import boto3

coloredlogs.install(level='INFO')

class Parameters:
    
    logger = logging.getLogger(__name__)

    def __init__(self,account_number,region,name_prefix="refex",local_path=None,date_string=None):
        working_dir = os.getcwd()

        try:
            self.access_key = boto3.Session().get_credentials().access_key
            self.logger.debug("AWS access key:",self.access_key)
        except Exception as err:
            self.logger.error("Unable to retrieve AWS credentials",err)
            self.access_key = None
        
        # AWS specific
        self.account_number = account_number
        self.region = region
        self.analysis_types = {
            "KeyPhraseResults":"KeyPhrases",
            "SentimentResults":"Sentiment",
            "TargetedSentimentResults":"Entities",
            "SyntaxResults":"SyntaxTokens"
        }
        # General parameters
        
        if not local_path:
            self.logger.warning("No path supplied, creating a data directory...")
            #print(f"WD: {working_dir}")
            data_dir = working_dir+"/data/"
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                self.logger.info("Created:",data_dir)
            self.local_path = data_dir
        else:
            data_dir = local_path
            if not os.path.exists(data_dir):
                self.logger.warning("Path does not exist, creating directory")
                os.makedirs(data_dir)
                self.logger.info(f"Created {data_dir}")
            self.local_path = local_path
        if not date_string:
            date_string = datetime.today().strftime('%Y%m%d')
            self.logger.warning(f"No date_string supplied, using today: {date_string}")
        self.date_string = date_string
        self.prefix = f"{name_prefix}_"
        self.postfix = f"-{date_string}"
        return None
    
    def all_parameters(self):
        return self.__dict__
    
    def set_s3_parameters(self,s3_access_point,bucket_name):
        self.s3_access_point = s3_access_point
        self.bucket_name = bucket_name
        self.s3_accesspoint_arn = f"arn:aws:s3:{self.region}:{self.account_number}:accesspoint/{s3_access_point}"
        
    def set_comprehend_parameters(self,comprehend_service_role_name):
        self.comprehend_service_role_name = comprehend_service_role_name
        self.comprehend_access_role_arn = f"arn:aws:iam::{self.account_number}:role/service-role/{comprehend_service_role_name}"
        
    def set_comprehend_custom_entity_parameters(self,reflexive_entity_name,reflexive_entity_version):
        self.reflexive_entity_name = reflexive_entity_name
        self.reflexive_entity_version = reflexive_entity_version
        self.reflexive_entity_arn = f"arn:aws:comprehend:{self.region}:{self.account_number}:entity-recognizer/{self.reflexive_entity_name}/version/{self.reflexive_entity_version}"