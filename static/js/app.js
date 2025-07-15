// Global state
let candidates = [];
let currentIndex = 0;
let stats = {
    reviewed: 0,
    saved: 0,
    passed: 0
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    checkJobDescription();
    setupKeyboardControls();
    startProcessingStatusUpdates();
});

// Check if job description exists
async function checkJobDescription() {
    try {
        const response = await fetch('/api/job-description');
        const data = await response.json();
        
        if (data.has_job_description) {
            // Show main content and load candidates
            document.getElementById('job-description-screen').style.display = 'none';
            document.getElementById('main-content').style.display = 'flex';
            loadCandidates();
            loadSavedCandidates();
        } else {
            // Show job description input screen
            document.getElementById('job-description-screen').style.display = 'flex';
            document.getElementById('main-content').style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking job description:', error);
    }
}

// Submit job description
async function submitJobDescription() {
    const jobDescription = document.getElementById('job-description-input').value.trim();
    
    if (!jobDescription) {
        alert('Please enter a job description');
        return;
    }
    
    const button = document.querySelector('.start-btn');
    button.classList.add('loading');
    button.disabled = true;
    
    try {
        const response = await fetch('/api/job-description', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_description: jobDescription })
        });
        
        if (response.ok) {
            // Hide job description screen and show main content
            document.getElementById('job-description-screen').style.display = 'none';
            document.getElementById('main-content').style.display = 'flex';
            
            // Start loading candidates
            loadCandidates();
            loadSavedCandidates();
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to save job description');
        }
    } catch (error) {
        console.error('Error submitting job description:', error);
        alert('Error submitting job description. Please try again.');
    } finally {
        button.classList.remove('loading');
        button.disabled = false;
    }
}

// Load candidates from API
async function loadCandidates() {
    try {
        const response = await fetch('/api/candidates');
        candidates = await response.json();
        currentIndex = 0; // Reset index on load
        
        if (candidates.length > 0) {
            displayCard(candidates[currentIndex]);
        } else {
            showNoMoreCards();
        }
    } catch (error) {
        console.error('Error loading candidates:', error);
        alert('Error loading candidates. Please refresh the page.');
    }
}

// Load saved candidates
async function loadSavedCandidates() {
    try {
        const response = await fetch('/api/saved');
        const saved = await response.json();
        displaySavedCandidates(saved);
    } catch (error) {
        console.error('Error loading saved candidates:', error);
    }
}

// Display candidate card
function displayCard(candidate) {
    const container = document.getElementById('card-container');
    const template = document.getElementById('card-template');
    
    // Clear existing cards
    container.innerHTML = '';
    
    // Clone template
    const card = template.content.cloneNode(true);
    
    // Calculate total experience from distribution
    let totalYears = 0;
    if (candidate.experience_distribution && typeof candidate.experience_distribution === 'object') {
        totalYears = Object.values(candidate.experience_distribution).reduce((sum, years) => sum + (years || 0), 0);
    }
    
    // Fill in candidate data
    card.querySelector('.candidate-name').textContent = candidate.name || candidate.nickname || 'Anonymous';
    card.querySelector('.experience-total').textContent = totalYears > 0 ? `${totalYears} years` : 'Experience TBD';
    card.querySelector('.summary-text').textContent = candidate.summary || 'No summary available';
    
    // Add reservations (black bullet points)
    const reservationsList = card.querySelector('.reservations-list');
    if (Array.isArray(candidate.reservations)) {
        candidate.reservations.forEach(reservation => {
            const li = document.createElement('li');
            li.textContent = reservation;
            reservationsList.appendChild(li);
        });
    }
    
    // Add fit indicators
    const fitIndicatorsList = card.querySelector('.fit-indicators-list');
    if (Array.isArray(candidate.fit_indicators)) {
        candidate.fit_indicators.forEach(indicator => {
            const li = document.createElement('li');
            li.textContent = indicator;
            fitIndicatorsList.appendChild(li);
        });
    }
    
    // Add achievements
    const achievementsList = card.querySelector('.achievements-list');
    if (Array.isArray(candidate.achievements)) {
        candidate.achievements.forEach(achievement => {
            const li = document.createElement('li');
            li.textContent = achievement;
            achievementsList.appendChild(li);
        });
    }
    
    // Add experience distribution
    const experienceDistribution = card.querySelector('.experience-distribution');
    if (candidate.experience_distribution && typeof candidate.experience_distribution === 'object') {
        const sectors = ['corporate', 'startup', 'nonprofit', 'government', 'education', 'other'];
        sectors.forEach(sector => {
            const years = candidate.experience_distribution[sector] || 0;
            if (years > 0) {
                const item = document.createElement('div');
                item.className = 'experience-item';
                item.innerHTML = `
                    <span class="experience-sector">${sector.charAt(0).toUpperCase() + sector.slice(1)}</span>
                    <span class="experience-years">${years} year${years !== 1 ? 's' : ''}</span>
                `;
                experienceDistribution.appendChild(item);
            }
        });
        
        if (experienceDistribution.children.length === 0) {
            experienceDistribution.innerHTML = '<p class="no-experience">Experience distribution unavailable</p>';
        }
    }
    
    // Add to container
    container.appendChild(card);
    
    // Setup drag functionality
    setupDragFunctionality();
}

// Setup drag/swipe functionality
function setupDragFunctionality() {
    const card = document.querySelector('.candidate-card');
    if (!card) return;
    
    let startX = 0;
    let currentX = 0;
    let isDragging = false;
    
    // Mouse events
    card.addEventListener('mousedown', handleStart);
    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleEnd);
    
    // Touch events
    card.addEventListener('touchstart', handleStart);
    document.addEventListener('touchmove', handleMove);
    document.addEventListener('touchend', handleEnd);
    
    function handleStart(e) {
        isDragging = true;
        card.classList.add('dragging');
        startX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
    }
    
    function handleMove(e) {
        if (!isDragging) return;
        
        currentX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
        const deltaX = currentX - startX;
        const rotation = deltaX * 0.1;
        
        card.style.transform = `translateX(${deltaX}px) rotate(${rotation}deg)`;
        card.style.opacity = 1 - Math.abs(deltaX) / 300;
    }
    
    function handleEnd() {
        if (!isDragging) return;
        
        isDragging = false;
        card.classList.remove('dragging');
        
        const deltaX = currentX - startX;
        const threshold = 100;
        
        if (Math.abs(deltaX) > threshold) {
            if (deltaX > 0) {
                performSwipe('right');
            } else {
                performSwipe('left');
            }
        } else {
            // Snap back
            card.style.transform = '';
            card.style.opacity = '';
        }
    }
}

// Perform swipe action
async function performSwipe(direction) {
    const card = document.querySelector('.candidate-card');
    const candidate = candidates[currentIndex];
    
    // Animate card out
    card.classList.add(direction === 'right' ? 'swiping-right' : 'swiping-left');
    
    // Update stats
    stats.reviewed++;
    if (direction === 'right') {
        stats.saved++;
    } else {
        stats.passed++;
    }
    updateStats();
    
    // Send decision to server
    try {
        await fetch('/api/swipe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                candidate_id: candidate.id,
                decision: direction === 'right' ? 'save' : 'pass'
            })
        });
        
        // Reload saved candidates if saved
        if (direction === 'right') {
            loadSavedCandidates();
        }
    } catch (error) {
        console.error('Error saving decision:', error);
    }
    
    // Move to next candidate
    setTimeout(() => {
        currentIndex++;
        if (currentIndex < candidates.length) {
            displayCard(candidates[currentIndex]);
        } else {
            showNoMoreCards();
        }
    }, 300);
}

// Button controls
function swipeLeft() {
    performSwipe('left');
}

function swipeRight() {
    performSwipe('right');
}

// Keyboard controls
function setupKeyboardControls() {
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') {
            swipeLeft();
        } else if (e.key === 'ArrowRight') {
            swipeRight();
        }
    });
}

// Update stats display
function updateStats() {
    document.getElementById('reviewed-count').textContent = stats.reviewed;
    document.getElementById('saved-count').textContent = stats.saved;
    document.getElementById('passed-count').textContent = stats.passed;
}

// Display saved candidates
function displaySavedCandidates(saved) {
    const container = document.getElementById('saved-candidates');
    container.innerHTML = '';
    
    if (saved.length === 0) {
        container.innerHTML = '<p class="empty-message">No candidates saved yet</p>';
        return;
    }
    
    saved.forEach(candidate => {
        const template = document.getElementById('saved-card-template');
        const card = template.content.cloneNode(true);
        
        // Calculate total experience from distribution
        let totalYears = 0;
        if (candidate.experience_distribution && typeof candidate.experience_distribution === 'object') {
            totalYears = Object.values(candidate.experience_distribution).reduce((sum, years) => sum + (years || 0), 0);
        }
        
        card.querySelector('.saved-name').textContent = candidate.name || candidate.nickname || 'Anonymous';
        card.querySelector('.saved-experience').textContent = totalYears > 0 ? `${totalYears} years experience` : 'Experience TBD';
        
        // Store candidate data for viewing
        const viewBtn = card.querySelector('.view-btn');
        viewBtn.dataset.candidateId = candidate.id;
        
        container.appendChild(card);
    });
}

// View candidate details
function viewCandidate(button) {
    const candidateId = button.dataset.candidateId;
    // In a real app, this would open a modal or navigate to a detail page
    alert(`View details for candidate ${candidateId}`);
}

// Show no more cards message
function showNoMoreCards() {
    const container = document.getElementById('card-container');
    container.innerHTML = '';
    document.getElementById('no-more-cards').style.display = 'block';
}

// Undo last swipe
async function undoLastSwipe() {
    try {
        const response = await fetch('/api/undo', { method: 'POST' });
        const result = await response.json();

        if (result.success) {
            // Reload candidates to reflect the undone swipe
            loadCandidates();
            loadSavedCandidates();
        } else {
            alert(result.message || 'Could not undo the last swipe.');
        }
    } catch (error) {
        console.error('Error undoing swipe:', error);
        alert('An error occurred while undoing the swipe.');
    }
}

// Confirm and restart session
function confirmRestart() {
    if (confirm('Are you sure you want to restart? This will clear all saved and passed candidates.')) {
        restartSession();
    }
}

async function restartSession() {
    try {
        await fetch('/api/restart', { method: 'POST' });
        window.location.reload(); // Easiest way to reset the UI
    } catch (error) {
        console.error('Error restarting session:', error);
        alert('An error occurred while restarting the session.');
    }
}

// Reset decisions
async function resetDecisions() {
    if (!confirm('Are you sure you want to reset all decisions?')) {
        return;
    }
    
    // In a real app, this would call an API to reset decisions
    // For now, just reload the page
    window.location.reload();
}

// Processing status updates
function startProcessingStatusUpdates() {
    updateProcessingStatus();
    
    // Update every 2 seconds
    setInterval(updateProcessingStatus, 2000);
}

async function updateProcessingStatus() {
    try {
        const response = await fetch('/api/process/status');
        const status = await response.json();
        
        document.getElementById('processing-status').textContent = status.status;
        document.getElementById('processing-progress').textContent = Math.round(status.progress) + '%';
        document.getElementById('progress-fill').style.width = status.progress + '%';
        
        // If processing is complete and we have unprocessed candidates, refresh
        if (status.status === 'completed' && hasUnprocessedCandidates()) {
            loadCandidates();
        }
    } catch (error) {
        console.error('Error updating processing status:', error);
    }
}

function hasUnprocessedCandidates() {
    // Check if current candidates have any with processing: true
    return candidates.some(candidate => candidate.processing === true);
}

// Force process next batch of candidates
async function forceProcessNextBatch() {
    const unprocessedCandidates = candidates.filter(c => c.processing === true);
    
    if (unprocessedCandidates.length === 0) {
        return;
    }
    
    const nextBatch = unprocessedCandidates.slice(0, 5).map(c => c.id);
    
    try {
        const response = await fetch('/api/process/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                candidate_ids: nextBatch
            })
        });
        
        const result = await response.json();
        console.log(`Processed ${result.processed_count} candidates`);
        
        // Refresh candidates
        setTimeout(() => {
            loadCandidates();
        }, 1000);
        
    } catch (error) {
        console.error('Error force processing batch:', error);
    }
} 