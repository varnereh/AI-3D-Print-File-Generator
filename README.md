# AI-Driven 3D Printing Capstone Project  

## Overview  
This project is our senior capstone for CSE 448/449. Our goal is to build a system that uses **AI text or image prompts to generate 3D models**, which can then be processed and sent through a pipeline for **3D printing**.  

We want to make 3D modeling more accessible by allowing users to describe what they want in natural language or 2D image upload to automatically generating printable models.  
This also eliminates the need to pay for 3D models online.

## Objectives  
- **AI Integration**: Convert text or image prompts into usable 3D models.  
- **Model Pipeline**: Process models for 3D printing and export them to printing software.  
- **User Interface**: Provide a simple and intuitive interface for users to input prompts and manage files.  
- **Export Options**: Support standard formats (e.g., `.stl`, `.obj`) for compatibility with common slicing software.  

## Scope  
- **In Scope**: AI-based 3D model generation (hosted locally), pipeline integration for printing, user-facing application.  
- **Out of Scope**: Developing new 3D printing hardware or custom slicers. Creating the AI model. Hosting model online.  

## Team Workflow  
We are using **GitLab** for collaboration, version control, and documentation.  

- Issues and boards will track research, development tasks, and bugs.  
- Branching strategy will follow:  
  - `main` branch → main code ready for testing/review  
  - feature branches → individual tasks and research items  
  - sprint branches → integration per sprint  

## Quality Goals  
- **Accuracy**: Generated models should reflect the user’s text prompt as closely as possible.  
- **Printability**: Models must be processed for watertight geometry suitable for slicing and printing.  
- **Usability**: Interface must be straightforward for non-technical users.  

## Getting Started  
1. Clone the repository:  
   ```bash
   git clone <repo-url>
   cd intelligent-3d-print
2. Install the dependencies
    ```bash
    pip install requirements.txt
3. Run application
4. Enter a text prompt or upload an image to generate model and review it.
5. Save the generated model in the file system.
6. Edit the advanced settings for the model generation
7. Export file to 3D printing software

## Contributors
- Lindsey Koenig
- Logan Lewton
- Spencer McCrae
- Ethan Varner

## Thank you!
