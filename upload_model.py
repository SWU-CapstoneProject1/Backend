from huggingface_hub import HfApi


api = HfApi()
repo_id = "sallychoe/koelectra-risk-pseudo"
api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, private=True)
api.upload_folder(
    folder_path="models/koelectra-risk-pseudo",
    repo_id=repo_id,
    repo_type="model",
    commit_message="Upload demo pseudo fine-tuned KR-ELECTRA risk classifier",
)
