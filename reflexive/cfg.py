import logging
import os
from datetime import datetime
import json
import reflexive as rfx

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Config:
    
    aws_profile = None
    aws_region = None
    aws_account_number = None
    aws_access_key = None
    
    local_path = None
    date_string = None
    analysis_types = None
    prefix = None
    postfix = None

    s3_access_point = None
    s3_bucket_name = None
    s3_accesspoint_arn = None

    comprehend_service_role_name = None
    comprehend_access_role_arn = None

    s3_files_folder = None
    s3_results_folder = None
    s3_input_uri = None
    s3_output_uri = None
    reflexive_entity_name = None
    reflexive_entity_version = None
    reflexive_entity_arn = None
    
    text_col_name = 'text'
    domain_terms = {}
    
    display_priority_tags = None
    display_colours = None
    display_options = None

    def __init__(self,profile="default"):
        self.aws_profile = profile
        
    def get_parameters(self):
        return self.__dict__

    def set_parameters(self,name_prefix="rfx",local_path=None,date_string=None):
        working_dir = os.getcwd()
        self.local_path = local_path
        self.date_string = date_string
        self.analysis_types = {
            "KeyPhraseResults":"KeyPhrases",
            "SentimentResults":"Sentiment",
            "TargetedSentimentResults":"Entities",
            "SyntaxResults":"SyntaxTokens"
        }
        
        # General parameters
        
        if not local_path:
            logger.warning("No path supplied, creating a data directory...")
            #print(f"WD: {working_dir}")
            data_dir = working_dir+"/data/"
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                logger.info("Created:%s",repr(data_dir))
            self.local_path = data_dir
        else:
            data_dir = local_path
            if not os.path.exists(data_dir):
                logger.warning("Path does not exist, creating directory")
                os.makedirs(data_dir)
                logger.info(f"Created %s",repr(data_dir))
            self.local_path = local_path
        if not date_string:
            date_string = datetime.today().strftime('%Y%m%d')
            logger.warning(f"No date_string supplied, using today: {date_string}")
        self.date_string = date_string
        self.prefix = f"{name_prefix}_"
        self.postfix = f"-{date_string}"
        return self.get_parameters()
        
        
    def set_s3_parameters(self,s3_access_point,s3_bucket_name):
        self.s3_access_point = s3_access_point
        self.s3_bucket_name = s3_bucket_name
        self.s3_accesspoint_arn = f"arn:aws:s3:{self.aws_region}:{self.aws_account_number}:accesspoint/{s3_access_point}"
        return self.get_parameters()
        
    def set_comprehend_parameters(self,comprehend_service_role_name):
        self.comprehend_service_role_name = comprehend_service_role_name
        self.comprehend_access_role_arn = f"arn:aws:iam::{self.aws_account_number}:role/service-role/{comprehend_service_role_name}"
        return self.get_parameters()
        
    def set_comprehend_custom_entity_parameters(self,reflexive_entity_name,reflexive_entity_version):
        #Comprehend requires S3 parameters
        self.s3_files_folder = f"{self.prefix}files{self.postfix}"
        self.s3_results_folder = f"{self.prefix}results{self.postfix}"
        self.s3_input_uri = f"s3://{self.s3_bucket_name}/{self.s3_files_folder}/{self.prefix}"
        self.s3_output_uri = f"s3://{self.s3_bucket_name}/{self.s3_results_folder}/"
        self.reflexive_entity_name = reflexive_entity_name
        self.reflexive_entity_version = reflexive_entity_version
        self.reflexive_entity_arn = f"arn:aws:comprehend:{self.aws_region}:{self.aws_account_number}:entity-recognizer/{self.reflexive_entity_name}/version/{self.reflexive_entity_version}"
        return self.get_parameters()
    
    def set_display_parameters(self,priority_tags,display_colours,display_options):
        self.display_priority_tags = priority_tags
        self.display_colours = display_colours
        self.display_options = display_options
        return self.get_parameters()
    
    
    
        