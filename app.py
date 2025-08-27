#!/usr/bin/env python3
"""
Python Deployment Platform - Similar to Netlify/Vercel
A platform for deploying web projects with GitHub integration
"""

import http.server
import socketserver
import json
import urllib.parse
import urllib.request
import os
import shutil
import threading
import time
import uuid
import mimetypes
from pathlib import Path

class DeploymentPlatform:
    def __init__(self):
        self.deployments = {}
        self.projects = {}
        self.users = {}
        self.github_tokens = {}
        self.base_port = 8001
        self.next_port = self.base_port
        
        # Create directories
        os.makedirs('deployments', exist_ok=True)
        os.makedirs('static', exist_ok=True)
        os.makedirs('uploads', exist_ok=True)
        
        # Load existing data
        self.load_data()

    def load_data(self):
        """Load deployment data from file"""
        try:
            if os.path.exists('platform_data.json'):
                with open('platform_data.json', 'r') as f:
                    data = json.load(f)
                    self.deployments = data.get('deployments', {})
                    self.projects = data.get('projects', {})
                    self.next_port = data.get('next_port', self.base_port)
        except Exception as e:
            print(f"Error loading data: {e}")

    def save_data(self):
        """Save deployment data to file"""
        try:
            data = {
                'deployments': self.deployments,
                'projects': self.projects,
                'next_port': self.next_port
            }
            with open('platform_data.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")

    def create_deployment(self, project_name, files_data=None, github_repo=None):
        """Create a new deployment"""
        deployment_id = str(uuid.uuid4())[:8]
        deploy_port = self.next_port
        self.next_port += 1
        
        deployment_dir = f"deployments/{deployment_id}"
        os.makedirs(deployment_dir, exist_ok=True)
        
        deployment = {
            'id': deployment_id,
            'project_name': project_name,
            'status': 'deploying',
            'port': deploy_port,
            'url': f'http://localhost:{deploy_port}',
            'created_at': time.time(),
            'github_repo': github_repo
        }
        
        self.deployments[deployment_id] = deployment
        self.save_data()
        
        # Deploy in background
        threading.Thread(target=self._deploy_project, args=(deployment_id, files_data)).start()
        
        return deployment

    def _deploy_project(self, deployment_id, files_data):
        """Deploy project files and start server"""
        try:
            deployment = self.deployments[deployment_id]
            deployment_dir = f"deployments/{deployment_id}"
            
            if files_data:
                # Handle uploaded files
                for filename, content in files_data.items():
                    file_path = os.path.join(deployment_dir, filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    if isinstance(content, str):
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                    else:
                        with open(file_path, 'wb') as f:
                            f.write(content)
            else:
                # Create a default index.html if no files provided
                with open(f"{deployment_dir}/index.html", 'w') as f:
                    f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{deployment['project_name']}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 40px; background: #f8fafc; }}
        .container {{ max-width: 800px; margin: 0 auto; text-align: center; }}
        h1 {{ color: #1e293b; margin-bottom: 16px; }}
        p {{ color: #64748b; font-size: 18px; }}
        .badge {{ background: #10b981; color: white; padding: 8px 16px; border-radius: 20px; display: inline-block; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 {deployment['project_name']}</h1>
        <p>Your project has been successfully deployed!</p>
        <div class="badge">Live on Python Deploy Platform</div>
    </div>
</body>
</html>""")
            
            # Start the deployment server
            self._start_deployment_server(deployment_id)
            
            # Update deployment status
            deployment['status'] = 'live'
            deployment['deployed_at'] = time.time()
            self.save_data()
            
        except Exception as e:
            print(f"Deployment error for {deployment_id}: {e}")
            self.deployments[deployment_id]['status'] = 'failed'
            self.deployments[deployment_id]['error'] = str(e)
            self.save_data()

    def _start_deployment_server(self, deployment_id):
        """Start a server for the deployed project"""
        deployment = self.deployments[deployment_id]
        deployment_dir = f"deployments/{deployment_id}"
        port = deployment['port']
        
        class DeploymentHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=deployment_dir, **kwargs)
            
            def log_message(self, format, *args):
                pass  # Suppress server logs
        
        def run_server():
            with socketserver.TCPServer(("", port), DeploymentHandler) as httpd:
                print(f"Deployment {deployment_id} serving at port {port}")
                httpd.serve_forever()
        
        threading.Thread(target=run_server, daemon=True).start()

    def get_github_repos(self, username):
        """Simulate GitHub API call to get repositories"""
        # In a real implementation, this would use GitHub API
        # For demo purposes, returning mock data
        return [
            {"name": "my-website", "description": "Personal website"},
            {"name": "react-app", "description": "React application"},
            {"name": "vue-project", "description": "Vue.js project"},
            {"name": "static-site", "description": "Static HTML site"}
        ]

# Global platform instance
platform = DeploymentPlatform()

class PlatformHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        if path == '/':
            self._serve_dashboard()
        elif path == '/api/deployments':
            self._api_get_deployments()
        elif path.startswith('/api/github/repos'):
            self._api_get_github_repos(query_params)
        elif path.startswith('/static/'):
            self._serve_static_file(path)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/deploy':
            self._api_deploy()
        elif path == '/api/github/auth':
            self._api_github_auth()
        elif path == '/api/upload':
            self._api_upload_files()
        else:
            self.send_error(404, "Not Found")

    def _serve_dashboard(self):
        """Serve the main dashboard"""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python Deploy Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #0f1419; color: #ffffff; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { border-bottom: 1px solid #252a32; padding: 20px 0; margin-bottom: 30px; }
        .header-content { display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 24px; font-weight: 700; color: #00d9ff; }
        .nav-links { display: flex; gap: 20px; }
        .nav-links a { color: #8b949e; text-decoration: none; transition: color 0.2s; }
        .nav-links a:hover { color: #ffffff; }
        .main-title { font-size: 48px; font-weight: 700; text-align: center; margin-bottom: 16px; background: linear-gradient(135deg, #00d9ff, #7c3aed); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { text-align: center; color: #8b949e; font-size: 20px; margin-bottom: 40px; }
        .deploy-section { background: #1c2128; border: 1px solid #252a32; border-radius: 12px; padding: 30px; margin-bottom: 30px; }
        .deploy-options { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .deploy-option { background: #252a32; padding: 20px; border-radius: 8px; cursor: pointer; transition: all 0.2s; border: 2px solid transparent; }
        .deploy-option:hover { border-color: #00d9ff; }
        .deploy-option.active { border-color: #7c3aed; background: #2a1f3d; }
        .deploy-option h3 { color: #ffffff; margin-bottom: 8px; }
        .deploy-option p { color: #8b949e; font-size: 14px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; color: #ffffff; font-weight: 500; }
        .form-group input, .form-group select { width: 100%; padding: 12px; background: #252a32; border: 1px solid #3d444d; border-radius: 6px; color: #ffffff; font-size: 14px; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: #00d9ff; }
        .btn { background: linear-gradient(135deg, #00d9ff, #7c3aed); border: none; color: white; padding: 12px 24px; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer; transition: opacity 0.2s; }
        .btn:hover { opacity: 0.9; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .deployments-section { margin-top: 40px; }
        .deployments-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .deployment-card { background: #1c2128; border: 1px solid #252a32; border-radius: 12px; padding: 20px; transition: transform 0.2s; }
        .deployment-card:hover { transform: translateY(-2px); }
        .deployment-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .deployment-title { font-weight: 600; color: #ffffff; }
        .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
        .status-live { background: #10b981; color: white; }
        .status-deploying { background: #f59e0b; color: white; }
        .status-failed { background: #ef4444; color: white; }
        .deployment-info { color: #8b949e; font-size: 14px; margin-bottom: 16px; }
        .deployment-url { background: #252a32; padding: 8px; border-radius: 4px; font-family: monospace; font-size: 12px; margin-bottom: 12px; }
        .deployment-actions { display: flex; gap: 8px; }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        .github-section { display: none; }
        .file-upload { border: 2px dashed #3d444d; border-radius: 8px; padding: 30px; text-align: center; color: #8b949e; cursor: pointer; transition: all 0.2s; }
        .file-upload:hover { border-color: #00d9ff; color: #00d9ff; }
        .file-upload.dragover { border-color: #7c3aed; background: #2a1f3d; }
        #fileInput { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <div class="logo">🚀 Python Deploy</div>
                <nav class="nav-links">
                    <a href="#deployments">Deployments</a>
                    <a href="#docs">Docs</a>
                    <a href="#github">GitHub</a>
                </nav>
            </div>
        </header>

        <div class="main-title">Deploy your projects instantly</div>
        <div class="subtitle">Connect your GitHub repository or upload files directly</div>

        <div class="deploy-section">
            <div class="deploy-options">
                <div class="deploy-option active" onclick="selectDeployOption('files')">
                    <h3>📁 Upload Files</h3>
                    <p>Upload your project files directly from your computer</p>
                </div>
                <div class="deploy-option" onclick="selectDeployOption('github')">
                    <h3>🐙 GitHub Repository</h3>
                    <p>Connect your GitHub account and deploy from repository</p>
                </div>
            </div>

            <div id="filesSection">
                <div class="form-group">
                    <label for="projectName">Project Name</label>
                    <input type="text" id="projectName" placeholder="my-awesome-project" required>
                </div>
                <div class="file-upload" onclick="document.getElementById('fileInput').click()">
                    <div>📤 Click to upload files or drag and drop</div>
                    <div style="font-size: 12px; margin-top: 8px;">Supports HTML, CSS, JS and other web files</div>
                </div>
                <input type="file" id="fileInput" multiple accept=".html,.css,.js,.json,.txt,.md">
                <div id="fileList" style="margin-top: 16px;"></div>
                <button class="btn" onclick="deployFiles()" style="margin-top: 16px;">Deploy Project</button>
            </div>

            <div id="githubSection" class="github-section">
                <div class="form-group">
                    <label for="githubUsername">GitHub Username</label>
                    <input type="text" id="githubUsername" placeholder="yourusername">
                </div>
                <div class="form-group">
                    <label for="githubRepo">Repository</label>
                    <select id="githubRepo">
                        <option value="">Select a repository...</option>
                    </select>
                </div>
                <button class="btn" onclick="deployGithub()">Deploy from GitHub</button>
            </div>
        </div>

        <div class="deployments-section">
            <h2 style="margin-bottom: 20px; color: #ffffff;">Recent Deployments</h2>
            <div class="deployments-grid" id="deploymentsGrid">
                <!-- Deployments will be loaded here -->
            </div>
        </div>
    </div>

    <script>
        let selectedFiles = {};
        let deploymentOption = 'files';

        function selectDeployOption(option) {
            deploymentOption = option;
            document.querySelectorAll('.deploy-option').forEach(el => el.classList.remove('active'));
            event.target.closest('.deploy-option').classList.add('active');
            
            if (option === 'files') {
                document.getElementById('filesSection').style.display = 'block';
                document.getElementById('githubSection').style.display = 'none';
            } else {
                document.getElementById('filesSection').style.display = 'none';
                document.getElementById('githubSection').style.display = 'block';
                loadGithubRepos();
            }
        }

        function loadGithubRepos() {
            const username = document.getElementById('githubUsername').value;
            if (!username) return;
            
            fetch(`/api/github/repos?username=${username}`)
                .then(r => r.json())
                .then(repos => {
                    const select = document.getElementById('githubRepo');
                    select.innerHTML = '<option value="">Select a repository...</option>';
                    repos.forEach(repo => {
                        select.innerHTML += `<option value="${repo.name}">${repo.name} - ${repo.description}</option>`;
                    });
                });
        }

        document.getElementById('githubUsername').addEventListener('input', loadGithubRepos);

        document.getElementById('fileInput').addEventListener('change', function(e) {
            const files = e.target.files;
            selectedFiles = {};
            let fileListHtml = '';
            
            for (let file of files) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    selectedFiles[file.name] = e.target.result;
                };
                
                if (file.type.startsWith('text/') || file.name.endsWith('.html') || file.name.endsWith('.css') || file.name.endsWith('.js')) {
                    reader.readAsText(file);
                } else {
                    reader.readAsDataURL(file);
                }
                
                fileListHtml += `<div style="background: #252a32; padding: 8px; margin: 4px 0; border-radius: 4px; font-size: 14px;">${file.name} (${(file.size/1024).toFixed(1)}KB)</div>`;
            }
            
            document.getElementById('fileList').innerHTML = fileListHtml;
        });

        function deployFiles() {
            const projectName = document.getElementById('projectName').value;
            if (!projectName) {
                alert('Please enter a project name');
                return;
            }
            
            if (Object.keys(selectedFiles).length === 0) {
                // Deploy with default template
                selectedFiles = {};
            }
            
            const deployData = {
                project_name: projectName,
                files: selectedFiles
            };
            
            fetch('/api/deploy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(deployData)
            })
            .then(r => r.json())
            .then(result => {
                alert(`Deployment started! Your project will be available at: ${result.url}`);
                loadDeployments();
                document.getElementById('projectName').value = '';
                document.getElementById('fileList').innerHTML = '';
                selectedFiles = {};
            });
        }

        function deployGithub() {
            const username = document.getElementById('githubUsername').value;
            const repo = document.getElementById('githubRepo').value;
            
            if (!username || !repo) {
                alert('Please select a GitHub repository');
                return;
            }
            
            const deployData = {
                project_name: repo,
                github_repo: `${username}/${repo}`
            };
            
            fetch('/api/deploy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(deployData)
            })
            .then(r => r.json())
            .then(result => {
                alert(`Deployment started! Your project will be available at: ${result.url}`);
                loadDeployments();
            });
        }

        function loadDeployments() {
            fetch('/api/deployments')
                .then(r => r.json())
                .then(deployments => {
                    const grid = document.getElementById('deploymentsGrid');
                    grid.innerHTML = '';
                    
                    Object.values(deployments).sort((a, b) => b.created_at - a.created_at).forEach(deployment => {
                        const card = document.createElement('div');
                        card.className = 'deployment-card';
                        
                        const statusClass = `status-${deployment.status}`;
                        const timeAgo = new Date(deployment.created_at * 1000).toLocaleString();
                        
                        card.innerHTML = `
                            <div class="deployment-header">
                                <div class="deployment-title">${deployment.project_name}</div>
                                <div class="status-badge ${statusClass}">${deployment.status}</div>
                            </div>
                            <div class="deployment-info">Deployed ${timeAgo}</div>
                            <div class="deployment-url">${deployment.url}</div>
                            <div class="deployment-actions">
                                <button class="btn btn-sm" onclick="window.open('${deployment.url}', '_blank')">View Live</button>
                                <button class="btn btn-sm" onclick="copyToClipboard('${deployment.url}')">Copy URL</button>
                            </div>
                        `;
                        
                        grid.appendChild(card);
                    });
                });
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('URL copied to clipboard!');
            });
        }

        // Load deployments on page load
        loadDeployments();
        setInterval(loadDeployments, 5000); // Refresh every 5 seconds
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-Length', len(html.encode()))
        self.end_headers()
        self.wfile.write(html.encode())

    def _api_get_deployments(self):
        """API endpoint to get all deployments"""
        response_data = json.dumps(platform.deployments)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', len(response_data))
        self.end_headers()
        self.wfile.write(response_data.encode())

    def _api_get_github_repos(self, query_params):
        """API endpoint to get GitHub repositories"""
        username = query_params.get('username', [''])[0]
        repos = platform.get_github_repos(username)
        
        response_data = json.dumps(repos)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', len(response_data))
        self.end_headers()
        self.wfile.write(response_data.encode())

    def _api_deploy(self):
        """API endpoint to create a new deployment"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode())
            project_name = data.get('project_name')
            files = data.get('files', {})
            github_repo = data.get('github_repo')
            
            deployment = platform.create_deployment(
                project_name=project_name,
                files_data=files,
                github_repo=github_repo
            )
            
            response_data = json.dumps(deployment)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-Length', len(response_data))
            self.end_headers()
            self.wfile.write(response_data.encode())
            
        except Exception as e:
            error_response = json.dumps({'error': str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-Length', len(error_response))
            self.end_headers()
            self.wfile.write(error_response.encode())

    def _api_github_auth(self):
        """API endpoint for GitHub authentication"""
        # In a real implementation, this would handle OAuth
        response_data = json.dumps({'status': 'authenticated'})
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', len(response_data))
        self.end_headers()
        self.wfile.write(response_data.encode())

    def _api_upload_files(self):
        """API endpoint for file uploads"""
        # This would handle file uploads in a real implementation
        response_data = json.dumps({'status': 'uploaded'})
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', len(response_data))
        self.end_headers()
        self.wfile.write(response_data.encode())

    def _serve_static_file(self, path):
        """Serve static files"""
        try:
            file_path = path[1:]  # Remove leading slash
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                content_type, _ = mimetypes.guess_type(file_path)
                if content_type is None:
                    content_type = 'application/octet-stream'
                
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "File not found")
        except Exception as e:
            self.send_error(500, str(e))

def start_platform():
    """Start the deployment platform"""
    port = 8000
    print(f"""
🚀 Python Deployment Platform Starting...

Dashboard: http://localhost:{port}
API Docs: http://localhost:{port}/api

Features:
✅ Project deployments with live URLs
✅ GitHub repository integration (simulated)
✅ File upload and management
✅ Real-time deployment status
✅ Shareable deployment links

Ready to deploy projects!
    """)
    
    with socketserver.TCPServer(("", port), PlatformHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Platform shutting down...")
            httpd.shutdown()

if __name__ == "__main__":
    start_platform()
