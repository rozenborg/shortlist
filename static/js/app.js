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
    loadCandidates();
    loadSavedCandidates();
    setupKeyboardControls();
    startProcessingStatusUpdates();
    checkCustomizationStatus();
});

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
    
    // Fill in candidate data
    card.querySelector('.candidate-name').textContent = candidate.name;
    card.querySelector('.score-value').textContent = candidate.fit_score + '/10';
    card.querySelector('.summary-text').textContent = candidate.summary;
    card.querySelector('.experience-level').textContent = candidate.experience_level;
    card.querySelector('.fit-reasoning').textContent = candidate.fit_reasoning;
    
    // Add skills
    const skillsContainer = card.querySelector('.skills-container');
    if (Array.isArray(candidate.skills)) {
        candidate.skills.forEach(skill => {
            const skillTag = document.createElement('div');
            skillTag.className = 'skill-tag';
            skillTag.textContent = skill;
            skillsContainer.appendChild(skillTag);
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
    const deck = document.getElementById('saved-deck');
    deck.innerHTML = '';
    
    if (saved.length === 0) {
        deck.innerHTML = '<p class="empty-message">No candidates saved yet</p>';
        return;
    }
    
    saved.forEach(candidate => {
        const template = document.getElementById('saved-card-template');
        const card = template.content.cloneNode(true);
        
        card.querySelector('.saved-name').textContent = candidate.name;
        card.querySelector('.saved-score span').textContent = candidate.fit_score;
        
        // Store candidate data for viewing
        const viewBtn = card.querySelector('.view-btn');
        viewBtn.dataset.candidateId = candidate.id;
        
        deck.appendChild(card);
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

// Reset decisions
async function resetDecisions() {
    if (!confirm('Are you sure you want to reset all decisions?')) {
        return;
    }
    
    // In a real app, this would call an API to reset decisions
    // For now, just reload the page
    window.location.reload();
}

// Customization Modal
async function openCustomizeModal() {
    const modal = document.getElementById('customize-modal');
    try {
        const response = await fetch('/api/customize');
        const settings = await response.json();
        document.getElementById('job-description').value = settings.job_description;
        document.getElementById('instructions').value = settings.instructions;
        modal.style.display = 'flex';
    } catch (error) {
        console.error('Error loading settings:', error);
        alert('Could not load customization settings.');
    }
}

function closeCustomizeModal() {
    document.getElementById('customize-modal').style.display = 'none';
}

async function saveCustomization() {
    const jobDescription = document.getElementById('job-description').value;
    const instructions = document.getElementById('instructions').value;
    const saveBtn = document.querySelector('.modal-btn');

    saveBtn.classList.add('loading');

    try {
        await fetch('/api/customize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_description: jobDescription,
                instructions: instructions
            })
        });
        closeCustomizeModal();
        checkCustomizationStatus();
        loadCandidates(); // Reload candidates to reflect new summaries
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Could not save customization settings.');
    } finally {
        saveBtn.classList.remove('loading');
    }
}

async function checkCustomizationStatus() {
    try {
        const response = await fetch('/api/customize');
        const settings = await response.json();
        const customizeBtn = document.getElementById('customize-btn');
        if (settings.job_description || settings.instructions) {
            customizeBtn.classList.add('configured');
        } else {
            customizeBtn.classList.remove('configured');
        }
    } catch (error) {
        console.error('Error checking customization status:', error);
    }
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
    if (confirm('Are you sure you want to restart? All saved and passed candidates will be cleared.')) {
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