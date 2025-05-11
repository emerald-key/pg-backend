# run dool in background
nohup dool --time --cpu --mem --disk --net --output llm_monitoring.csv > /dev/null 2>&1 &

#run llm script in backrgound
nohup python3 main.py > llmoutputNew.log 2>&1 &








