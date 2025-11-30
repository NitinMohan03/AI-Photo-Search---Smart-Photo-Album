# 🖼️ AI Photo Search

A serverless, intelligent photo search application built on AWS.  
Users can upload images and search them using natural-language queries such as **“show me photos with dogs in a park.”**

This project demonstrates event-driven architecture, AI-powered image analysis, and scalable, fully serverless design using AWS managed services.

---

## 🚀 Features

- 🔍 **Natural Language Search** using Amazon Lex  
- 🏷️ **Automatic Image Labeling** with Rekognition  
- ⚡ **Real-Time Indexing** into Amazon OpenSearch  
- 🖥️ **S3-Hosted Web Interface** with drag-and-drop uploads  
- ☁️ **Fully Serverless Architecture** (Lambda, API Gateway, S3, Lex, Rekognition, OpenSearch)

---

## 🏗️ Architecture Overview



User → S3 Web App → API Gateway
| |
▼ ▼
S3 Bucket Lambda (LF2 - search)
| |
▼ ▼
Lambda (LF1 - index) → Rekognition → OpenSearch


---

## 📦 Project Structure



ai-photo-search/
├── frontend/ # Static web UI (HTML, CSS, JS)
│ ├── index.html
│ ├── script.js
│ ├── styles.css
│ └── config.js
│
├── lambda/
│ ├── index-photos/ # LF1 - Extract labels & index in OpenSearch
│ │ ├── index-photos.py
│ │ └── requirements.txt
│ └── search-photos/ # LF2 - Search endpoint
│ ├── search-photos.py
│ └── requirements.txt
│
├── cloudformation-template.yaml
└── README.md


---

## ⚙️ Deployment (Quick Start)

### 1. Deploy Infrastructure (CloudFormation)

```bash
aws cloudformation create-stack \
  --stack-name ai-photo-search \
  --template-body file://cloudformation-template.yaml \
  --capabilities CAPABILITY_NAMED_IAM
```

Wait for stack completion:

aws cloudformation wait stack-create-complete --stack-name ai-photo-search

2. Upload Frontend
aws s3 sync frontend/ s3://YOUR_WEBSITE_BUCKET/

3. Update Frontend Config

Edit frontend/config.js:

const CONFIG = {
    API_ENDPOINT: "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/v1",
    PHOTO_BUCKET: "YOUR_PHOTO_BUCKET",
    REGION: "us-east-1"
};

🧪 Usage
Upload Photos

Open the S3 static website URL

Drag and drop a photo

(Optional) Add custom labels

Click Upload

Behind the scenes:

Photo → S3

S3 triggers Lambda LF1

LF1 → Rekognition → extracts labels

LF1 → stores labels in OpenSearch

Search Photos

Use natural-language queries like:

trees

dogs in a park

flowers and mountains

show me photos with cats

LF2 sends query → Lex → extracts keywords → searches OpenSearch → returns matching photos.

🔐 Security

IAM least-privilege Lambda roles

API Gateway HTTPS enforcement

S3 bucket access controls

OpenSearch fine-grained access control

CORS configured for frontend domain

📈 Monitoring

CloudWatch Logs for LF1 and LF2

CloudWatch Metrics for API Gateway & Lambda

Optional: X-Ray for tracing

📄 License

This project is licensed under the MIT License.

🙏 Acknowledgments

Built as part of a cloud computing academic project

AWS documentation and OpenSearch community resources

⭐ If you found this project useful, please give it a star!

