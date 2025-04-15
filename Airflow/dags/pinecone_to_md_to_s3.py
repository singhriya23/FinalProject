from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os, fitz, boto3, traceback
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from dotenv import load_dotenv

load_dotenv(dotenv_path="Airflow/dags/.env")

# ====== CONFIG ======
ROOT_DIR = "/opt/airflow/dags/University_Folders"
TMP_MD_DIR = "/opt/airflow/shared_markdowns"
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

# === Setup DAG ===
default_args = {
    'start_date': datetime(2025, 4, 13),
    'retries': 1
}

dag = DAG(
    "university_pdf_to_s3_only",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
    description="Convert university PDFs to Markdown and upload to S3 (no Pinecone)"
)

# === Step 1: Convert PDFs to Markdown ===
def scan_and_convert():
    if not os.path.exists(TMP_MD_DIR):
        os.makedirs(TMP_MD_DIR, exist_ok=True)

    print(f"📁 Scanning in: {ROOT_DIR}")
    for root, _, files in os.walk(ROOT_DIR):
        for file in files:
            if file.endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                relative_path = os.path.relpath(pdf_path, ROOT_DIR)
                university = relative_path.split(os.sep)[0]
                doc_type = os.path.splitext(os.path.basename(file))[0]
                output_md_path = os.path.join(TMP_MD_DIR, f"{university}_{doc_type}.md")

                try:
                    print(f"🔍 Converting: {pdf_path}")
                    doc = fitz.open(pdf_path)

                    # ✅ Extract all text from all pages
                    text = "\n\n".join([page.get_text("text") for page in doc])

                    if text.strip():
                        with open(output_md_path, "w", encoding="utf-8") as f:
                            f.write(text)
                        print(f"✅ Saved Markdown: {output_md_path}")
                    else:
                        print(f"⚠️ No extractable text in {pdf_path}")

                except Exception as e:
                    print(f"❌ Failed to convert {pdf_path}: {e}")
                    traceback.print_exc()

# === Step 2: Upload Markdown files to S3 ===


def upload_to_s3():
    s3_hook = S3Hook(aws_conn_id='aws_default')  # or your custom connection ID

    for filename in os.listdir(TMP_MD_DIR):
        if filename.endswith(".md"):
            local_path = os.path.join(TMP_MD_DIR, filename)
            university, doc_type = filename.replace(".md", "").split("_", 1)
            s3_key = f"University_Folders/{university}/{doc_type}.md"

            try:
                s3_hook.load_file(
                    filename=local_path,
                    key=s3_key,
                    bucket_name=S3_BUCKET,
                    replace=True
                )
                print(f"☁️ Uploaded to S3: {s3_key}")
            except Exception as e:
                print(f"❌ Failed to upload {filename} to S3: {e}")


# === DAG Tasks ===
task_convert = PythonOperator(
    task_id="scan_and_convert_pdfs",
    python_callable=scan_and_convert,
    dag=dag
)

task_upload = PythonOperator(
    task_id="upload_markdowns_to_s3",
    python_callable=upload_to_s3,
    dag=dag
)

task_convert >> task_upload
