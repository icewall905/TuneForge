// Clean Problematic Files Methods for AudioAnalysisManager class
// Replace the corrupted section in templates/audio_analysis.html with these methods

    // Problematic Files Management
    refreshProblematicFiles() {
        fetch('/api/audio-analysis/problematic-files')
            .then(response => response.json())
            .then(data => {
                this.displayProblematicFiles(data);
            })
            .catch(error => {
                console.error('Error fetching problematic files:', error);
                this.displayProblematicFiles({ error: 'Failed to load problematic files report' });
            });
    },

    displayProblematicFiles(data) {
        const container = document.getElementById('problematic-files-content');
        
        if (data.error) {
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle"></i>
                    Error: ${data.error}
                </div>
            `;
            return;
        }

        let html = '';

        // Summary section
        if (data.summary) {
            const summary = data.summary;
            html += `
                <div class="row mb-3">
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h4 text-primary">${summary.total_tracks || 0}</div>
                            <small class="text-muted">Total Tracks</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h4 text-warning">${summary.pending_tracks || 0}</div>
                            <small class="text-muted">Pending</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h4 text-success">${summary.completed_tracks || 0}</div>
                            <small class="text-muted">Completed</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h4 text-danger">${summary.error_tracks || 0}</div>
                            <small class="text-muted">Errors</small>
                        </div>
                    </div>
                </div>
            `;
        }

        // Problematic files section
        if (data.problematic_files && data.problematic_files.length > 0) {
            html += `
                <div class="mb-4">
                    <h6 class="text-warning">
                        <i class="fas fa-exclamation-triangle"></i>
                        Problematic Files (${data.problematic_files.length})
                    </h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>Filename</th>
                                    <th>Failures</th>
                                    <th>Last Failure</th>
                                    <th>Error Message</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            data.problematic_files.forEach(file => {
                const filename = file.filename || 'Unknown';
                const shortPath = file.file_path ? file.file_path.substring(0, 50) + '...' : 'Unknown';
                
                html += `
                    <tr>
                        <td>
                            <div class="fw-bold">${filename}</div>
                            <small class="text-muted">${shortPath}</small>
                        </td>
                        <td>
                            <span class="badge bg-danger">${file.failure_count}</span>
                        </td>
                        <td>
                            <small>${file.last_failure || 'Unknown'}</small>
                        </td>
                        <td>
                            <small class="text-danger">${file.error_message ? file.error_message.substring(0, 60) + '...' : 'No error message'}</small>
                        </td>
                        <td>
                            <button class="btn btn-sm btn-outline-warning" 
                                    onclick="audioManager.forceSkipFile('${file.file_path}', '${filename}')"
                                    title="Skip this file permanently">
                                <i class="fas fa-ban"></i> Skip
                            </button>
                        </td>
                    </tr>
                `;
            });
            
            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Stuck files section
        if (data.stuck_files && data.stuck_files.length > 0) {
            html += `
                <div class="mb-4">
                    <h6 class="text-info">
                        <i class="fas fa-clock"></i>
                        Stuck Files (${data.stuck_files.length})
                    </h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>Filename</th>
                                    <th>Time Stuck</th>
                                    <th>Last Update</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            data.stuck_files.forEach(file => {
                const filename = file.filename || 'Unknown';
                const shortPath = file.file_path ? file.file_path.substring(0, 50) + '...' : 'Unknown';
                const timeClass = file.minutes_stuck > 300 ? 'text-danger' : 'text-warning';
                
                html += `
                    <tr>
                        <td>
                            <div class="fw-bold">${filename}</div>
                            <small class="text-muted">${shortPath}</small>
                        </td>
                        <td>
                            <span class="${timeClass}">${file.minutes_stuck.toFixed(1)} min</span>
                        </td>
                        <td>
                            <small>${file.last_updated || 'Unknown'}</small>
                        </td>
                        <td>
                            <button class="btn btn-sm btn-outline-info" 
                                    onclick="audioManager.forceResetFile('${file.file_path}', '${filename}')"
                                    title="Reset this file to pending status">
                                <i class="fas fa-redo"></i> Reset
                            </button>
                        </td>
                    </tr>
                `;
            });
            
            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Error patterns section
        if (data.error_patterns && data.error_patterns.length > 0) {
            html += `
                <div class="mb-4">
                    <h6 class="text-danger">
                        <i class="fas fa-bug"></i>
                        Error Patterns (${data.error_patterns.length})
                    </h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>Error Message</th>
                                    <th>Frequency</th>
                                    <th>Last Occurrence</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            data.error_patterns.forEach(pattern => {
                const freqClass = pattern.frequency === 'high' ? 'bg-danger' : 
                               pattern.frequency === 'medium' ? 'bg-warning' : 'bg-info';
                
                html += `
                    <tr>
                        <td>
                            <small class="text-danger">${pattern.error_message.substring(0, 80)}...</small>
                        </td>
                        <td>
                            <span class="badge ${freqClass}">${pattern.count}</span>
                        </td>
                        <td>
                            <small>${pattern.last_occurrence || 'Unknown'}</small>
                        </td>
                    </tr>
                `;
            });
            
            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Recommendations section
        if (data.recommendations && data.recommendations.length > 0) {
            html += `
                <div class="mb-3">
                    <h6 class="text-primary">
                        <i class="fas fa-lightbulb"></i>
                        Recommendations
                    </h6>
                    <ul class="list-unstyled">
            `;
            
            data.recommendations.forEach(rec => {
                html += `
                    <li class="mb-2">
                        <i class="fas fa-arrow-right text-primary"></i>
                        ${rec}
                    </li>
                `;
            });
            
            html += `
                    </ul>
                </div>
            `;
        }

        // No issues message
        if ((!data.problematic_files || data.problematic_files.length === 0) &&
            (!data.stuck_files || data.stuck_files.length === 0) &&
            (!data.error_patterns || data.error_patterns.length === 0)) {
            html += `
                <div class="text-center text-success py-4">
                    <i class="fas fa-check-circle fa-3x mb-3"></i>
                    <h5>No Problematic Files Detected</h5>
                    <p class="text-muted">Your audio analysis system is running smoothly!</p>
                </div>
            `;
        }

        container.innerHTML = html;
    },

    forceSkipFile(filePath, filename) {
        if (!confirm(`Are you sure you want to permanently skip "${filename}"?\n\nThis will mark the file as skipped and it won't be processed again.`)) {
            return;
        }

        fetch('/api/audio-analysis/force-skip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_path: filePath,
                reason: 'Manually skipped by user to prevent stall'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showAlert('success', `File "${filename}" skipped successfully`);
                this.refreshProblematicFiles();
                this.refreshHealth(); // Refresh health status
            } else {
                this.showAlert('danger', `Failed to skip file: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error skipping file:', error);
            this.showAlert('danger', 'Error skipping file. Please try again.');
        });
    },

    forceResetFile(filePath, filename) {
        if (!confirm(`Are you sure you want to reset "${filename}"?\n\nThis will move the file back to pending status for retry.`)) {
            return;
        }

        fetch('/api/audio-analysis/force-reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_path: filePath,
                reason: 'Manually reset by user from stuck state'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showAlert('success', `File "${filename}" reset successfully`);
                this.refreshProblematicFiles();
                this.refreshHealth(); // Refresh health status
            } else {
                this.showAlert('danger', `Failed to reset file: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error resetting file:', error);
            this.showAlert('danger', 'Error resetting file. Please try again.');
        });
    },

    showAlert(type, message) {
        const messagesContainer = document.getElementById('status-messages');
        const messageElement = document.createElement('div');
        messageElement.className = `status-message status-${type}`;
        messageElement.textContent = message;
        
        messagesContainer.appendChild(messageElement);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.parentNode.removeChild(messageElement);
            }
        }, 5000);
    },
