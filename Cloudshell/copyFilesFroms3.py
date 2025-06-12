# Set your bucket name
bucket_name="llm-model-outputs"

# List of files
files=(
filename.csv
)

# Copy each file
for file in "${files[@]}"; do
  aws s3 cp "s3://$bucket_name/redshift-loads/$file" "s3://$bucket_name/redshift-loads/missing_lead_summary/$file"
done