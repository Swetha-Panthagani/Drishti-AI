# Project Drishti

## Overview

*Improving safety at large public events.*

Project Drishti is an AI-powered situational awareness platform that acts as a central nervous system for event safety. This platform provides actionable intelligence to commanders, enabling them to anticipate and mitigate risks in real-time.

## Features

- *Centralized Dashboard*: A comprehensive dashboard for event commanders to monitor crowd density, movement, and potential anomalies across different zones.
- *AI-Powered Video Analysis*: Utilizes the Gemini 1.5 Flash model to analyze video feeds from different event zones, providing real-time summaries of crowd behavior.
- *Crowd Heatmap*: Visualizes crowd density in different zones, allowing for quick identification of potential chokepoints or overcrowding.
- *Missing Person Reporting*: A user-facing portal for attendees to upload photos of missing persons.
- *AI-Powered Image Comparison*: Admins can compare images of missing persons with a database of found individuals, using the Gemini model to identify potential matches.
- *Separate User and Admin Portals*: A dedicated landing page directs users to either the public-facing reporting page or the secure admin dashboard.

## Architecture

The application is built on a three-tier architecture:

1.  *Client (Web Browser)*: The user interface is built with HTML, CSS, and JavaScript, providing a responsive experience for both admins and users.
2.  *Backend (Flask Application)*: A Python-based backend built with the Flask framework. It handles all business logic, including user requests, file uploads, and communication with Google Cloud services.
3.  *Google Cloud Platform (GCP)*: The backend is powered by several GCP services:
    -   *Vertex AI (Gemini 1.5 Flash)*: Used for all AI-powered analysis, including video summaries and image comparisons.
    -   *Cloud Storage*: Serves as the central repository for all video files and uploaded images for comparison.

## Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites

-   Python 3.10+
-   A Google Cloud Platform (GCP) account with the Vertex AI API enabled.
-   A Google Cloud Storage bucket.
-   The gcloud CLI, authenticated with your GCP account.

### Installation

1.  *Clone the Repository*
    bash
    git clone <your-repository-url>
    cd <your-repository-name>
    

2.  *Set Up Google Cloud Credentials*
    -   Create a service account in your GCP project with the "Vertex AI User" and "Storage Object Admin" roles.
    -   Download the JSON key for this service account and save it in the root of the project directory as ace-well-467010-f5-7cf97226dec2.json.

3.  *Create a Python Virtual Environment*
    bash
    python3 -m venv .venv
    source .venv/bin/activate
    

4.  *Install Dependencies*
    bash
    pip install -r requirements.txt
    

5.  *Create Necessary Directories*
    bash
    mkdir -p static/user_uploads
    mkdir -p static/admin_uploads
    

6.  *Run the Application*
    bash
    python main.py
    
    The application will be available at http://127.0.0.1:8080.

## Usage

1.  *Landing Page*: Open your web browser to http://127.0.0.1:8080. You will be greeted with the Project Drishti landing page.

2.  *User Flow*:
    -   Click on *Report Missing Person*.
    -   Select up to two photos of the missing person and click *Upload*.

3.  *Admin Flow*:
    -   From the landing page, click on *Admin*.
    -   This will take you to the main dashboard, where you can view video summaries and the crowd heatmap.
    -   Click on the *Admin Panel* link in the header to navigate to the image comparison page.
    -   Here, you can upload photos of found individuals and compare them against the user-uploaded photos to find a match.

## Technology Stack

-   *Backend*: Python, Flask
-   *Frontend*: HTML, CSS, JavaScript
-   *AI*: Google Cloud Vertex AI (Gemini 1.5 Flash)
-   *Storage*: Google Cloud Storage
-   *Dependency Management*: pip# Drishti-AI
