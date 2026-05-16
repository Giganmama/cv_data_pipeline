from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import os
import sys

# Add project root to path so scripts are importable
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from video_processor import VideoProcessor
from metadata_extractor import MetadataExtractor
from data_quality_checks import DataQualityChecker
from s3_handler import S3Handler

default_args = {
    "owner": "robotics_team",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "cv_data_pipeline",
    default_args=default_args,
    description="End-to-end CV data processing pipeline",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["robotics", "cv", "etl"],
)

# --- Tasks Definition ---

def task_extract_metadata(**kwargs):
    extractor = MetadataExtractor()
    # Example video path (in reality this would come from a sensor or trigger)
    video_path = "/opt/airflow/scripts/sample_video.mp4" 
    if os.path.exists(video_path):
        return extractor.extract(video_path)
    return {"status": "no_video_found"}

def task_process_video(**kwargs):
    processor = VideoProcessor(output_dir="/tmp/frames", fps=1) # 1 frame per sec
    # Example usage
    # processor.extract_frames("input.mp4")
    return {"status": "processed"}

def task_quality_check(**kwargs):
    checker = DataQualityChecker()
    # checker.audit_directory("/tmp/frames")
    return {"quality_status": "checked"}

def task_upload_to_s3(**kwargs):
    handler = S3Handler()
    # handler.upload_directory("/tmp/frames", prefix="dataset_v1")
    return {"status": "uploaded"}

# --- DAG Execution Flow ---

t1 = PythonOperator(
    task_id="extract_metadata",
    python_callable=task_extract_metadata,
    dag=dag,
)

t2 = PythonOperator(
    task_id="extract_frames",
    python_callable=task_process_video,
    dag=dag,
)

t3 = PythonOperator(
    task_id="check_quality",
    python_callable=task_quality_check,
    dag=dag,
)

t4 = PythonOperator(
    task_id="upload_to_minio",
    python_callable=task_upload_to_s3,
    dag=dag,
)

# Dependencies: Extract Metadata -> Process Video -> Check Quality -> Upload
t1 >> t2 >> t3 >> t4
