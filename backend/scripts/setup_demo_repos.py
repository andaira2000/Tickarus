#!/usr/bin/env python3
"""
Script to create dummy GitHub repositories for dissertation testing
This script will create realistic repositories with different tech stacks
"""

import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict
import subprocess
import json

# Add the parent directory to Python path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

# Demo organization name
ORG_NAME = "tickarus-demo-org"

# Repository templates with realistic content
REPO_TEMPLATES = {
    "frontend-webapp": {
        "language": "TypeScript",
        "description": "React TypeScript web application for customer portal",
        "files": {
            "package.json": {
                "name": "frontend-webapp",
                "version": "1.0.0",
                "scripts": {
                    "start": "react-scripts start",
                    "build": "react-scripts build",
                    "test": "react-scripts test",
                    "lint": "eslint src --ext .ts,.tsx"
                },
                "dependencies": {
                    "react": "^18.2.0",
                    "@types/react": "^18.2.0",
                    "typescript": "^5.0.0",
                    "axios": "^1.6.0"
                }
            },
            ".github/workflows/ci.yml": '''name: Frontend CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: |
          # Simulate occasional test failures for demo
          if [ $((RANDOM % 8)) -eq 0 ]; then
            echo "Simulated test failure" && exit 1
          fi
          npm test -- --coverage
      - name: Build
        run: npm run build''',
            "src/App.tsx": '''import React from 'react';

function App() {
  return (
    <div className="App">
      <h1>Customer Portal</h1>
      <p>Welcome to the Tickarus demo application</p>
    </div>
  );
}

export default App;''',
            "README.md": '''# Frontend Web App

React TypeScript application for the customer portal.

## Setup
```bash
npm install
npm start
```''',
            ".eslintrc.js": '''module.exports = {
  extends: ["react-app", "react-app/jest"],
  rules: {
    "@typescript-eslint/no-unused-vars": "error"
  }
};'''
        }
    },
    
    "backend-api": {
        "language": "Python",
        "description": "FastAPI backend service for ticket management",
        "files": {
            "requirements.txt": '''fastapi>=0.110.0
uvicorn[standard]>=0.25.0
pydantic>=2.6.0
sqlalchemy>=2.0.0
alembic>=1.13.0
pytest>=7.4.0''',
            ".github/workflows/ci.yml": '''name: Backend CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          # Simulate database connection issues occasionally
          if [ $((RANDOM % 10)) -eq 0 ]; then
            echo "Database connection failed" && exit 1
          fi
          pytest tests/
      - name: Lint
        run: |
          pip install flake8
          flake8 app/''',
            "app/main.py": '''from fastapi import FastAPI

app = FastAPI(title="Ticket API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Ticket API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}''',
            "README.md": '''# Backend API

FastAPI backend service for the ticketing system.

## Setup
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```''',
            "tests/test_main.py": '''import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()'''
        }
    },
    
    "mobile-app": {
        "language": "JavaScript",
        "description": "React Native mobile application",
        "files": {
            "package.json": {
                "name": "mobile-app",
                "version": "1.0.0",
                "main": "index.js",
                "scripts": {
                    "start": "expo start",
                    "android": "expo start --android",
                    "ios": "expo start --ios",
                    "test": "jest"
                },
                "dependencies": {
                    "expo": "~49.0.0",
                    "react": "18.2.0",
                    "react-native": "0.72.0"
                }
            },
            ".github/workflows/ci.yml": '''name: Mobile CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: |
          # Simulate iOS build issues occasionally  
          if [ $((RANDOM % 12)) -eq 0 ]; then
            echo "iOS build failed: provisioning profile error" && exit 1
          fi
          npm test''',
            "App.js": '''import React from 'react';
import { Text, View, StyleSheet } from 'react-native';

export default function App() {
  return (
    <View style={styles.container}>
      <Text>Tickarus Mobile App</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});''',
            "README.md": '''# Mobile App

React Native mobile application.

## Setup
```bash
npm install
expo start
```'''
        }
    },
    
    "data-pipeline": {
        "language": "Python", 
        "description": "ETL pipeline for analytics data processing",
        "files": {
            "requirements.txt": '''pandas>=2.0.0
sqlalchemy>=2.0.0
apache-airflow>=2.7.0
psycopg2-binary>=2.9.0''',
            ".github/workflows/ci.yml": '''name: Data Pipeline CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run pipeline tests
        run: |
          # Simulate data quality issues
          if [ $((RANDOM % 15)) -eq 0 ]; then
            echo "Data validation failed: missing required columns" && exit 1
          fi
          python -m pytest tests/''',
            "pipeline/etl.py": '''import pandas as pd
from datetime import datetime

def extract_data():
    """Extract data from various sources"""
    return pd.DataFrame({
        'timestamp': [datetime.now()],
        'metric': ['tickets_created'],
        'value': [42]
    })

def transform_data(df):
    """Transform and clean data"""
    return df.dropna()

def load_data(df):
    """Load data to destination"""
    print(f"Loading {len(df)} rows")''',
            "README.md": '''# Data Pipeline

ETL pipeline for processing analytics data.

## Setup
```bash
pip install -r requirements.txt
python pipeline/etl.py
```'''
        }
    },
    
    "ml-models": {
        "language": "Python",
        "description": "Machine learning models for ticket classification", 
        "files": {
            "requirements.txt": '''scikit-learn>=1.3.0
pandas>=2.0.0
numpy>=1.24.0
jupyter>=1.0.0
matplotlib>=3.7.0''',
            ".github/workflows/ci.yml": '''name: ML Models CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Train model
        run: |
          # Simulate model training failures
          if [ $((RANDOM % 20)) -eq 0 ]; then
            echo "Model training failed: insufficient data" && exit 1
          fi
          python train_model.py''',
            "train_model.py": '''import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

def train_ticket_classifier():
    # Dummy training data
    data = pd.DataFrame({
        'text': ['bug in login', 'feature request', 'performance issue'],
        'category': ['bug', 'feature', 'performance']
    })
    
    # Simple classifier
    model = RandomForestClassifier()
    print("Model training completed")

if __name__ == "__main__":
    train_ticket_classifier()''',
            "README.md": '''# ML Models

Machine learning models for ticket classification and analysis.

## Setup
```bash
pip install -r requirements.txt
python train_model.py
```'''
        }
    },
    
    "legacy-java-service": {
        "language": "Java",
        "description": "Legacy Spring Boot microservice for user management",
        "files": {
            "pom.xml": '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <groupId>com.tickarus</groupId>
    <artifactId>legacy-user-service</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>2.7.0</version>
    </parent>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
    </dependencies>
</project>''',
            ".github/workflows/ci.yml": '''name: Java Service CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          java-version: '11'
          distribution: 'temurin'
      - name: Build with Maven
        run: |
          # Simulate dependency conflicts
          if [ $((RANDOM % 18)) -eq 0 ]; then
            echo "Maven build failed: dependency conflict" && exit 1
          fi
          mvn clean compile''',
            "src/main/java/UserService.java": '''package com.tickarus;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class UserService {
    public static void main(String[] args) {
        SpringApplication.run(UserService.class, args);
    }
}''',
            "README.md": '''# Legacy User Service

Spring Boot microservice for user management.

## Setup
```bash
mvn clean install
mvn spring-boot:run
```'''
        }
    }
}


def create_repository_files(repo_path: Path, repo_data: Dict):
    """Create files for a repository"""
    for file_path, content in repo_data["files"].items():
        full_path = repo_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(content, dict):
            # JSON files
            with open(full_path, 'w') as f:
                json.dump(content, f, indent=2)
        else:
            # Text files
            with open(full_path, 'w') as f:
                f.write(content)


def run_git_command(repo_path: Path, command: List[str]):
    """Run a git command in the repository"""
    try:
        result = subprocess.run(
            ["git"] + command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {' '.join(command)}")
        print(f"Error: {e.stderr}")
        return None


async def create_demo_repositories():
    """Create all demo repositories"""
    print(f"Creating demo repositories for organization: {ORG_NAME}")
    
    # Create temporary directory for repositories
    temp_dir = Path(tempfile.mkdtemp(prefix="tickarus_repos_"))
    print(f"Working in temporary directory: {temp_dir}")
    
    try:
        for repo_name, repo_data in REPO_TEMPLATES.items():
            print(f"\nCreating repository: {repo_name}")
            
            repo_path = temp_dir / repo_name
            repo_path.mkdir()
            
            # Create repository files
            create_repository_files(repo_path, repo_data)
            
            # Initialize git repository
            run_git_command(repo_path, ["init"])
            run_git_command(repo_path, ["add", "."])
            run_git_command(repo_path, ["commit", "-m", "Initial commit: Setup repository structure"])
            
            # Add some realistic commit history
            await create_commit_history(repo_path, repo_name)
            
            print(f"Repository {repo_name} created successfully")
            print(f"   Language: {repo_data['language']}")
            print(f"   Files: {len(repo_data['files'])}")
            
        print(f"\nAll {len(REPO_TEMPLATES)} repositories created!")
        print(f"\nNext steps:")
        print(f"1. Create GitHub organization: {ORG_NAME}")
        print(f"2. Push repositories to GitHub:")
        
        for repo_name in REPO_TEMPLATES.keys():
            print(f"   cd {temp_dir / repo_name}")
            print(f"   git remote add origin https://github.com/{ORG_NAME}/{repo_name}.git")
            print(f"   git push -u origin main")
            print()
            
    except Exception as e:
        print(f"Error creating repositories: {e}")
    finally:
        # Keep the temporary directory for manual upload
        print(f"Repository files are available at: {temp_dir}")


async def create_commit_history(repo_path: Path, repo_name: str):
    """Create realistic commit history for the repository"""
    commits = [
        ("feat: Add basic project structure", "Add initial project files and configuration"),
        ("fix: Update dependencies to latest versions", "Security updates and bug fixes"),
        ("docs: Update README with setup instructions", "Improve documentation"),
        ("test: Add unit tests for core functionality", "Increase test coverage"),
        ("refactor: Clean up code structure", "Improve maintainability"),
    ]
    
    for i, (commit_msg, description) in enumerate(commits):
        # Make small changes to files
        readme_path = repo_path / "README.md"
        if readme_path.exists():
            with open(readme_path, 'a') as f:
                f.write(f"\n\n<!-- Commit {i+1}: {description} -->")
        
        run_git_command(repo_path, ["add", "."])
        run_git_command(repo_path, ["commit", "-m", commit_msg])


def print_manual_setup_instructions():
    """Print instructions for manual GitHub setup"""
    print(f"""
MANUAL SETUP INSTRUCTIONS

1. Create GitHub Organization:
   - Go to https://github.com/organizations/new
   - Organization name: {ORG_NAME}
   - Make it public for testing

2. For each repository, run these commands:
""")
    
    for repo_name in REPO_TEMPLATES.keys():
        print(f"""
   Repository: {repo_name}
   ---
   # Create empty repo on GitHub first, then:
   cd path/to/{repo_name}
   git remote add origin https://github.com/{ORG_NAME}/{repo_name}.git
   git branch -M main
   git push -u origin main
""")

    print(f"""
3. Set up GitHub webhook for CI failures:
   - Go to each repository Settings > Webhooks
   - Add webhook URL: https://your-api-domain.com/api/github/webhooks/ci-failure
   - Content type: application/json
   - Events: Workflow runs
   - Set webhook secret in your .env file

4. Update your .env file:
   GITHUB_TOKEN=your_github_personal_access_token
   GITHUB_ORG_NAME={ORG_NAME}
   GITHUB_WEBHOOK_SECRET=your_webhook_secret
""")


if __name__ == "__main__":
    print("Tickarus Demo Repository Setup")
    print("=" * 50)
    
    # Check if we can run git commands
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Git is not installed or not in PATH")
        print("Please install Git and try again")
        sys.exit(1)
    
    # Run the repository creation
    asyncio.run(create_demo_repositories())
    
    # Print manual setup instructions
    print_manual_setup_instructions()