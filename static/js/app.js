// Global state
let candidates = [];
let currentIndex = 0;
let stats = {
    reviewed: 0,
    saved: 0,
    starred: 0,
    passed: 0,
    leftToReview: 0,
    failed: 0
};
let passedCandidates = [];
let savedCandidates = [];
let hasShownProcessingNotification = false;

// Real-time processing variables
let realTimeUpdateInterval = null;
let processingStatsInterval = null;
let lastCandidateCount = 0;
let newCandidatesAvailable = false;

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
        
        if (data.has_job_description && !window.showJobDescriptionScreen) {
            // Show main content and load candidates
            document.getElementById('job-description-screen').style.display = 'none';
            document.getElementById('main-content').style.display = 'flex';
            loadCandidates();
            loadSavedCandidates();
        } else {
            // Show job description input screen
            document.getElementById('job-description-screen').style.display = 'flex';
            document.getElementById('main-content').style.display = 'none';
            
            // Populate with existing job description if available
            if (data.job_description) {
                document.getElementById('job-description-input').value = data.job_description;
                // Update button text to indicate this is an edit/restart
                const buttonText = document.querySelector('.start-btn .btn-text');
                if (buttonText) {
                    buttonText.textContent = 'Continue with Updated Job Description';
                }
            } else {
                // Reset button text for first time setup
                const buttonText = document.querySelector('.start-btn .btn-text');
                if (buttonText) {
                    buttonText.textContent = 'Start Reviewing Candidates';
                }
            }
        }
        
        // Reset the flag
        window.showJobDescriptionScreen = false;
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
    const buttonText = document.querySelector('.start-btn .btn-text');
    const isRestart = buttonText.textContent.includes('Continue');
    
    button.classList.add('loading');
    button.disabled = true;
    
    try {
        const response = await fetch('/api/job-description', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_description: jobDescription })
        });
        
        if (response.ok) {
            // Reset processing tracking state
            window.wasProcessing = false;
            window.hasShownCompleted = false;
            hasShownProcessingNotification = false;
            
            // Hide job description screen and show main content
            document.getElementById('job-description-screen').style.display = 'none';
            document.getElementById('main-content').style.display = 'flex';
            
            // Reset button text for next time
            buttonText.textContent = 'Start Reviewing Candidates';
            
            // Show notification if this was a restart/update
            if (isRestart) {
                showNotification('Job description updated! Re-analyzing all candidates with the new criteria...', 'info');
            }
            
            // Start loading candidates
            loadCandidates();
            loadSavedCandidates();
            updateRightTabCounts();
            
            // Force an immediate status update to show processing has started
            setTimeout(() => {
                updateProcessingStatus();
            }, 100);
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

// Load candidates from API with real-time support
async function loadCandidates(preferReady = true) {
    try {
        // Prefer ready candidates by default for better user experience
        let apiUrl = preferReady ? '/api/candidates/ready' : '/api/candidates';
        
        const response = await fetch(apiUrl);
        const newCandidates = await response.json();
        
        // Check for newly available candidates
        const readyCount = newCandidates.filter(c => c.ready_for_review !== false).length;
        if (readyCount > lastCandidateCount && lastCandidateCount > 0) {
            newCandidatesAvailable = true;
            showNotification(`${readyCount - lastCandidateCount} new candidates are ready for review!`, 'success');
        }
        lastCandidateCount = readyCount;
        
        // Update candidates array efficiently
        if (newCandidates.length === 0 && candidates.length === 0) {
            // No candidates yet, start real-time updates
            console.log('🔄 No candidates ready yet, starting real-time updates');
            startRealTimeUpdates();
        } else if (newCandidates.length > 0) {
            // We have candidates - merge them properly
            const previousLength = candidates.length;
            candidates = mergeCandidates(candidates, newCandidates);
            
            // If we got new candidates and were showing "no more cards", refresh the display
            if (candidates.length > previousLength && document.getElementById('no-more-cards').style.display !== 'none') {
                console.log('📥 New candidates available, refreshing display');
                if (currentIndex >= candidates.length) {
                    currentIndex = 0;
                }
                displayCard(candidates[currentIndex]);
                return;
            }
        }
        
        // Reset index if we're at the end and new candidates arrived
        if (currentIndex >= candidates.length && candidates.length > 0) {
            currentIndex = 0;
        }
        
        // Check if any candidates are still processing
        const processingCount = candidates.filter(c => c.processing === true || c.ready_for_review === false).length;
        if (processingCount > 0 && !hasShownProcessingNotification) {
            showNotification(`${processingCount} candidates are still being analyzed. They'll update automatically when ready.`, 'info');
            hasShownProcessingNotification = true;
            
            // Start real-time updates if not already running
            if (!realTimeUpdateInterval) {
                startRealTimeUpdates();
            }
        } else if (processingCount === 0) {
            // Reset flag when no candidates are processing
            hasShownProcessingNotification = false;
            
            // Stop real-time updates if no more processing
            if (realTimeUpdateInterval) {
                stopRealTimeUpdates();
            }
        }
        
        if (candidates.length > 0) {
            updateLeftToReviewCount();
            displayCard(candidates[currentIndex]);
        } else {
            await showNoMoreCards();
        }
        updateStats();
    } catch (error) {
        console.error('Error loading candidates:', error);
        alert('Error loading candidates. Please refresh the page.');
    }
}

// Merge new candidates with existing ones, preserving position
function mergeCandidates(existing, newCandidates) {
    const existingIds = new Set(existing.map(c => c.id));
    const merged = [...existing];
    
    // Add new candidates that we haven't seen before
    for (const candidate of newCandidates) {
        if (!existingIds.has(candidate.id)) {
            // Insert ready candidates at the beginning, processing ones at the end
            if (candidate.ready_for_review !== false) {
                merged.unshift(candidate);
            } else {
                merged.push(candidate);
            }
        } else {
            // Update existing candidate data
            const index = merged.findIndex(c => c.id === candidate.id);
            if (index !== -1) {
                merged[index] = candidate;
            }
        }
    }
    
    return merged;
}

// Start real-time updates for processing candidates
function startRealTimeUpdates() {
    if (realTimeUpdateInterval) return; // Already running
    
    console.log('🔄 Starting real-time candidate updates');
    
    realTimeUpdateInterval = setInterval(async () => {
        try {
            // Check for newly processed candidates
            const response = await fetch('/api/candidates/newly-processed');
            const newlyProcessed = await response.json();
            
            if (newlyProcessed.length > 0) {
                console.log(`📥 ${newlyProcessed.length} new candidates processed`);
                
                // Add newly processed candidates to the front of the queue
                for (const candidate of newlyProcessed.reverse()) {
                    candidates.unshift(candidate);
                }
                
                // Show notification
                showNotification(`${newlyProcessed.length} new candidates ready for review!`, 'success');
                
                // If we're currently showing "no more cards", switch to showing the first candidate
                const noMoreCardsElement = document.getElementById('no-more-cards');
                if (noMoreCardsElement.style.display !== 'none') {
                    console.log('🔄 Was showing no-more-cards, now displaying first candidate');
                    currentIndex = 0;
                    updateLeftToReviewCount();
                    displayCard(candidates[currentIndex]);
                } else if (currentIndex >= candidates.length - newlyProcessed.length) {
                    // Update display if we're at the end
                    updateLeftToReviewCount();
                    displayCard(candidates[currentIndex]);
                }
                updateStats();
            }
            
            // Also check for ready candidates from the regular endpoint
            const readyResponse = await fetch('/api/candidates/ready');
            const readyCandidates = await readyResponse.json();
            
            if (readyCandidates.length > candidates.length) {
                console.log(`📥 Found ${readyCandidates.length - candidates.length} additional ready candidates`);
                candidates = mergeCandidates(candidates, readyCandidates);
                
                // If we're showing no-more-cards, switch to showing candidates
                const noMoreCardsElement = document.getElementById('no-more-cards');
                if (noMoreCardsElement.style.display !== 'none' && candidates.length > 0) {
                    console.log('🔄 Found ready candidates, switching from no-more-cards to candidate display');
                    currentIndex = 0;
                    displayCard(candidates[currentIndex]);
                }
            }
            
            // Update processing candidates
            const processingResponse = await fetch('/api/candidates/processing');
            const processingCandidates = await processingResponse.json();
            
            // Update processing count in UI
            updateProcessingStatus(processingCandidates.length);
            
            // Stop updates if no more processing
            if (processingCandidates.length === 0) {
                console.log('⏹️ No more candidates processing, stopping real-time updates');
                stopRealTimeUpdates();
                
                // If we're still showing the processing state, refresh it
                const noMoreCardsElement = document.getElementById('no-more-cards');
                if (noMoreCardsElement.style.display !== 'none' && noMoreCardsElement.innerHTML.includes('Analyzing Candidates')) {
                    await showNoMoreCards();
                }
            }
            
        } catch (error) {
            console.error('Error in real-time update:', error);
        }
    }, 2000); // Check every 2 seconds for more responsiveness
}

// Stop real-time updates
function stopRealTimeUpdates() {
    if (realTimeUpdateInterval) {
        clearInterval(realTimeUpdateInterval);
        realTimeUpdateInterval = null;
        console.log('⏹️ Stopped real-time candidate updates');
    }
}

// Update processing status in UI
function updateProcessingStatus(processingCount) {
    const statusElement = document.querySelector('.processing-status');
    if (statusElement && processingCount > 0) {
        statusElement.textContent = `Processing ${processingCount} candidates...`;
        statusElement.style.display = 'block';
    } else if (statusElement) {
        statusElement.style.display = 'none';
    }
}

// Load saved candidates
async function loadSavedCandidates() {
    try {
        const response = await fetch('/api/saved');
        const saved = await response.json();
        displaySavedCandidates(saved);
        updateSavedCount(saved.length);
    } catch (error) {
        console.error('Error loading saved candidates:', error);
    }
}

// Display candidate card
function displayCard(candidate) {
    console.log('Displaying candidate:', candidate); // Debug log
    console.log('Candidate differentiators:', candidate.differentiators); // Debug log
    
    const container = document.getElementById('card-container');
    const template = document.getElementById('card-template');
    
    // Clear existing cards
    container.innerHTML = '';
    
    // Clone template
    const card = template.content.cloneNode(true);
    
    // Fill in candidate data
    card.querySelector('.candidate-name').textContent = candidate.name || candidate.nickname || 'Anonymous';
    
    // Add differentiators to the header section instead of creating separate section
    const cardHeader = card.querySelector('.card-header');
    console.log('Card header found:', !!cardHeader); // Debug log
    console.log('Differentiators check:', candidate.differentiators, candidate.differentiators?.length); // Debug log
    
    if (candidate.differentiators && candidate.differentiators.length > 0) {
        console.log('Adding differentiators to header with', candidate.differentiators.length, 'items'); // Debug log
        const differentiatorsList = document.createElement('ul');
        differentiatorsList.className = 'differentiators-list';
        
        candidate.differentiators.forEach(diff => {
            console.log('Adding differentiator:', diff); // Debug log
            const li = document.createElement('li');
            li.className = 'evidence-item';
            li.setAttribute('data-evidence', diff.evidence || '');
            li.textContent = diff.claim || diff;
            differentiatorsList.appendChild(li);
        });
        
        cardHeader.appendChild(differentiatorsList);
        console.log('Differentiators added to header'); // Debug log
    } else {
        console.log('No differentiators to display'); // Debug log
    }
    
    card.querySelector('.summary-text').textContent = candidate.summary || 'No summary available';
    
    // Add reservations (no evidence for gaps)
    const reservationsList = card.querySelector('.reservations-list');
    if (Array.isArray(candidate.reservations)) {
        candidate.reservations.forEach(reservation => {
            const li = document.createElement('li');
            // Reservations don't have evidence since they're about gaps/missing things
            li.textContent = reservation;
            reservationsList.appendChild(li);
        });
    }
    
    // Add relevant achievements with evidence
    const relevantAchievementsList = card.querySelector('.relevant-achievements-list');
    if (Array.isArray(candidate.relevant_achievements)) {
        candidate.relevant_achievements.forEach(achievement => {
            const li = document.createElement('li');
            li.className = 'evidence-item';
            if (typeof achievement === 'object') {
                li.setAttribute('data-evidence', achievement.evidence || '');
                li.textContent = achievement.achievement || achievement;
            } else {
                li.textContent = achievement;
            }
            relevantAchievementsList.appendChild(li);
        });
    }
    
    // Add work history
    const workHistoryList = card.querySelector('.work-history-list');
    if (Array.isArray(candidate.work_history) && candidate.work_history.length > 0) {
        candidate.work_history.forEach(job => {
            const jobItem = document.createElement('div');
            jobItem.className = 'work-history-item';
            jobItem.innerHTML = `
                <div class="job-title">${job.title || 'Title not available'}</div>
                <div class="company-name">${job.company || 'Company not available'}</div>
                ${job.years ? `<div class="job-years">${job.years}</div>` : ''}
            `;
            workHistoryList.appendChild(jobItem);
        });
    } else {
        workHistoryList.innerHTML = '<p class="no-work-history">Work history not available</p>';
    }
    
    // Add wildcard
    const wildcardText = card.querySelector('.wildcard-text');
    if (candidate.wildcard && typeof candidate.wildcard === 'object') {
        wildcardText.className = 'wildcard-text evidence-item';
        wildcardText.setAttribute('data-evidence', candidate.wildcard.evidence || '');
        wildcardText.textContent = candidate.wildcard.fact || 'No wildcard information available';
    } else {
        wildcardText.textContent = candidate.wildcard || 'No wildcard information available';
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
    
    // Setup evidence tooltips
    setupEvidenceTooltips();
    
    // Show action buttons when displaying cards
    const actionButtons = document.querySelector('.action-buttons');
    if (actionButtons) {
        actionButtons.style.display = 'flex';
    }
    document.getElementById('no-more-cards').style.display = 'none';
    
    // Setup drag functionality
    setupDragFunctionality();
}

// Setup evidence tooltips
function setupEvidenceTooltips() {
    // Create tooltip element if it doesn't exist
    let tooltip = document.getElementById('evidence-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'evidence-tooltip';
        tooltip.className = 'evidence-tooltip';
        document.body.appendChild(tooltip);
    }
    
    // Add hover listeners to all evidence items
    const evidenceItems = document.querySelectorAll('.evidence-item[data-evidence]');
    evidenceItems.forEach(item => {
        const evidence = item.getAttribute('data-evidence');
        if (evidence && evidence.trim()) {
            item.classList.add('has-evidence');
            
            item.addEventListener('mouseenter', (e) => {
                tooltip.textContent = `"${evidence}"`;
                tooltip.style.display = 'block';
                
                // Position tooltip near the cursor
                const rect = item.getBoundingClientRect();
                tooltip.style.left = rect.left + 'px';
                tooltip.style.top = (rect.bottom + 5) + 'px';
                
                // Adjust if tooltip goes off screen
                const tooltipRect = tooltip.getBoundingClientRect();
                if (tooltipRect.right > window.innerWidth) {
                    tooltip.style.left = (window.innerWidth - tooltipRect.width - 10) + 'px';
                }
                if (tooltipRect.bottom > window.innerHeight) {
                    tooltip.style.top = (rect.top - tooltipRect.height - 5) + 'px';
                }
            });
            
            item.addEventListener('mouseleave', () => {
                tooltip.style.display = 'none';
            });
        }
    });
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
    
    // Animate card out based on direction
    if (direction === 'left') {
        card.classList.add('swiping-left');
    } else if (direction === 'right') {
        card.classList.add('swiping-right');
    } else if (direction === 'star') {
        // Add a special animation for starring
        card.classList.add('swiping-star');
    }
    
    // Update stats
    stats.reviewed++;
    if (direction === 'right') {
        stats.saved++;
    } else if (direction === 'star') {
        stats.starred++;
    } else {
        stats.passed++;
    }
    updateLeftToReviewCount();
    updateStats();
    
    // Send decision to server
    try {
        let decision;
        if (direction === 'right') {
            decision = 'save';
        } else if (direction === 'star') {
            decision = 'star';
        } else {
            decision = 'pass';
        }
        
        await fetch('/api/swipe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                candidate_id: candidate.id,
                decision: decision
            })
        });
        
        // Reload saved candidates if saved or starred
        if (direction === 'right' || direction === 'star') {
            loadSavedCandidates();
        }
        
        // Update passed count if passed
        if (direction === 'left') {
            // Fetch updated passed count
            fetch('/api/passed')
                .then(response => response.json())
                .then(passedData => {
                    updatePassedCount(passedData.length);
                })
                .catch(error => {
                    console.error('Error updating passed count:', error);
                });
        }
    } catch (error) {
        console.error('Error saving decision:', error);
    }
    
    // Move to next candidate
    setTimeout(() => {
        currentIndex++;
        updateLeftToReviewCount();
        if (currentIndex < candidates.length) {
            displayCard(candidates[currentIndex]);
        } else {
            showNoMoreCards();
        }
        updateStats();
    }, 300);
}

// Button controls
function swipeLeft() {
    performSwipe('left');
}

function swipeRight() {
    performSwipe('right');
}

function swipeStar() {
    performSwipe('star');
}

// Keyboard controls
function setupKeyboardControls() {
    document.addEventListener('keydown', (e) => {
        // Check if modal is open
        const modal = document.getElementById('candidate-modal');
        const isModalOpen = modal && modal.style.display === 'block';
        
        if (isModalOpen && e.key === 'Escape') {
            closeCandidateModal();
        } else if (!isModalOpen) {
            // Only handle swipe keys when modal is not open
            if (e.key === 'ArrowLeft') {
                swipeLeft();
            } else if (e.key === 'ArrowRight') {
                swipeRight();
            }
        }
    });
}

// Update left to review count
function updateLeftToReviewCount() {
    stats.leftToReview = Math.max(0, candidates.length - currentIndex);
}

// Update stats display
function updateStats() {
    document.getElementById('reviewed-count').textContent = stats.reviewed;
    document.getElementById('saved-count').textContent = stats.saved;
    document.getElementById('starred-count').textContent = stats.starred;
    document.getElementById('passed-count').textContent = stats.passed;
    document.getElementById('left-to-review-count').textContent = stats.leftToReview;
    document.getElementById('failed-count').textContent = stats.failed;
    
    // Show/hide failed export link based on failed count
    const failedExportLink = document.getElementById('failed-export-link');
    if (stats.failed > 0) {
        failedExportLink.style.display = 'block';
    } else {
        failedExportLink.style.display = 'none';
    }
}

// Display saved candidates
function displaySavedCandidates(saved) {
    const container = document.getElementById('saved-candidates');
    container.innerHTML = '';
    
    // Store in global array for modal access
    savedCandidates = saved;
    
    if (saved.length === 0) {
        container.innerHTML = '<p class="empty-message">No candidates saved yet</p>';
        return;
    }
    
    saved.forEach((candidate, index) => {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'saved-card';
        cardDiv.draggable = true;
        cardDiv.dataset.candidateId = candidate.id;
        cardDiv.dataset.index = index;
        
        // Add star if candidate is starred
        const candidateName = candidate.name || candidate.nickname || 'Anonymous';
        const displayName = candidate.is_starred ? `⭐ ${candidateName}` : candidateName;
        
        // Determine action text based on whether it was saved or starred
        let actionText = 'Saved';
        if (candidate.is_starred && candidate.is_saved) {
            actionText = 'Saved & Starred';
        } else if (candidate.is_starred) {
            actionText = 'Starred';
        }
        
        cardDiv.innerHTML = `
            <div class="drag-handle">⋮⋮</div>
            <div class="saved-card-content">
                <h4 class="saved-name">${displayName}</h4>
                <div class="saved-experience">${actionText} ${formatTimestamp(candidate.saved_at)}</div>
                <div class="candidate-actions">
                    <button class="action-btn view-btn-subtle" onclick="viewCandidateFromPanel('${candidate.id}', 'saved')">View</button>
                    <button class="action-btn star-btn-subtle" onclick="modifyDecision('${candidate.id}', '${candidate.is_starred ? 'save' : 'star'}')">${candidate.is_starred ? 'Unstar' : 'Star'}</button>
                    <button class="action-btn pass-btn-subtle" onclick="modifyDecision('${candidate.id}', 'pass')">Pass</button>
                </div>
            </div>
        `;
        
        // Add drag event listeners
        setupDragListeners(cardDiv);
        
        container.appendChild(cardDiv);
    });
    
    // Setup container-level drag events for better drop zone handling
    setupContainerDragEvents();
}

// Setup drag and drop listeners for a card
function setupDragListeners(cardElement) {
    cardElement.addEventListener('dragstart', handleDragStart);
    cardElement.addEventListener('dragend', handleDragEnd);
}

// Setup container-level drag events for better drop handling
function setupContainerDragEvents() {
    const container = document.getElementById('saved-candidates');
    
    // Remove existing listeners to avoid duplicates
    container.removeEventListener('dragover', handleContainerDragOver);
    container.removeEventListener('drop', handleContainerDrop);
    
    // Add container-level listeners
    container.addEventListener('dragover', handleContainerDragOver);
    container.addEventListener('drop', handleContainerDrop);
}

function handleContainerDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    
    // Find the closest drop zone
    const afterElement = getDragAfterElement(this, e.clientY);
    let dropIndicator = document.querySelector('.drop-indicator');
    
    // Create drop indicator if it doesn't exist
    if (!dropIndicator) {
        dropIndicator = document.createElement('div');
        dropIndicator.className = 'drop-indicator';
        dropIndicator.innerHTML = '<div class="drop-line"></div>';
    }
    
    if (afterElement == null) {
        this.appendChild(dropIndicator);
    } else {
        this.insertBefore(dropIndicator, afterElement);
    }
    
    return false;
}

function handleContainerDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    
    const dropIndicator = document.querySelector('.drop-indicator');
    
    if (dropIndicator && draggedElement) {
        // Insert the dragged element where the drop indicator is
        this.insertBefore(draggedElement, dropIndicator);
        dropIndicator.remove();
        
        // Update the order on the server
        updateCandidateOrder();
    }
    
    return false;
}

// Drag and drop handlers
let draggedElement = null;
let dragCounter = 0;

function handleDragStart(e) {
    draggedElement = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.outerHTML);
}

function handleDragEnd(e) {
    // Clean up
    const allCards = document.querySelectorAll('.saved-card');
    allCards.forEach(card => {
        card.classList.remove('dragging', 'drag-over');
    });
    
    // Remove drop indicator if it exists
    const dropIndicator = document.querySelector('.drop-indicator');
    if (dropIndicator) {
        dropIndicator.remove();
    }
    
    draggedElement = null;
    dragCounter = 0;
}

// Get the element that should come after the dragged element
function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.saved-card:not(.dragging)')];
    
    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// Update candidate order on server
async function updateCandidateOrder() {
    const container = document.getElementById('saved-candidates');
    const cards = Array.from(container.querySelectorAll('.saved-card'));
    const orderedIds = cards.map(card => card.dataset.candidateId);
    
    try {
        await fetch('/api/saved/reorder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ordered_ids: orderedIds
            })
        });
    } catch (error) {
        console.error('Error updating candidate order:', error);
        showNotification('Error saving new order. Please refresh the page.', 'error');
    }
}



// Open candidate details modal
function openCandidateModal(candidate) {
    const modal = document.getElementById('candidate-modal');
    
    // Populate modal content
    document.getElementById('modal-candidate-name').textContent = candidate.name || candidate.nickname || 'Anonymous';
    document.getElementById('modal-summary').textContent = candidate.summary || 'No summary available';
    // Handle wildcard which can be object or string
    const wildcardText = typeof candidate.wildcard === 'object' 
        ? candidate.wildcard.fact || 'No wildcard information available'
        : candidate.wildcard || 'No wildcard information available';
    document.getElementById('modal-wildcard').textContent = wildcardText;
    
    // Populate fit indicators (using differentiators from API)
    const fitIndicatorsList = document.getElementById('modal-fit-indicators');
    fitIndicatorsList.innerHTML = '';
    if (Array.isArray(candidate.differentiators)) {
        candidate.differentiators.forEach(diff => {
            const li = document.createElement('li');
            li.textContent = typeof diff === 'object' ? diff.claim : diff;
            fitIndicatorsList.appendChild(li);
        });
    }
    
    // Populate reservations
    const reservationsList = document.getElementById('modal-reservations');
    reservationsList.innerHTML = '';
    if (Array.isArray(candidate.reservations)) {
        candidate.reservations.forEach(reservation => {
            const li = document.createElement('li');
            li.textContent = reservation;
            reservationsList.appendChild(li);
        });
    }
    
    // Populate achievements (using relevant_achievements from API)
    const achievementsList = document.getElementById('modal-achievements');
    achievementsList.innerHTML = '';
    if (Array.isArray(candidate.relevant_achievements)) {
        candidate.relevant_achievements.forEach(achievement => {
            const li = document.createElement('li');
            li.textContent = typeof achievement === 'object' ? achievement.achievement : achievement;
            achievementsList.appendChild(li);
        });
    }
    
    // Populate work history
    const workHistoryDiv = document.getElementById('modal-work-history');
    workHistoryDiv.innerHTML = '';
    if (Array.isArray(candidate.work_history) && candidate.work_history.length > 0) {
        candidate.work_history.forEach(job => {
            const jobItem = document.createElement('div');
            jobItem.className = 'modal-work-history-item';
            jobItem.innerHTML = `
                <div class="modal-job-title">${job.title || 'Title not available'}</div>
                <div class="modal-company-name">${job.company || 'Company not available'}</div>
                ${job.years ? `<div class="modal-job-years">${job.years}</div>` : ''}
            `;
            workHistoryDiv.appendChild(jobItem);
        });
    } else {
        workHistoryDiv.innerHTML = '<p style="color: #999; font-style: italic;">Work history not available</p>';
    }
    
    // Populate experience distribution
    const experienceDistribution = document.getElementById('modal-experience-distribution');
    experienceDistribution.innerHTML = '';
    if (candidate.experience_distribution && typeof candidate.experience_distribution === 'object') {
        const sectors = ['corporate', 'startup', 'nonprofit', 'government', 'education', 'other'];
        sectors.forEach(sector => {
            const years = candidate.experience_distribution[sector] || 0;
            if (years > 0) {
                const item = document.createElement('div');
                item.className = 'modal-experience-item';
                item.innerHTML = `
                    <span class="modal-experience-sector">${sector.charAt(0).toUpperCase() + sector.slice(1)}</span>
                    <span class="modal-experience-years">${years} year${years !== 1 ? 's' : ''}</span>
                `;
                experienceDistribution.appendChild(item);
            }
        });
        
        if (experienceDistribution.children.length === 0) {
            experienceDistribution.innerHTML = '<p style="color: #999; font-style: italic;">Experience distribution unavailable</p>';
        }
    } else {
        experienceDistribution.innerHTML = '<p style="color: #999; font-style: italic;">Experience distribution unavailable</p>';
    }
    
    // Show modal
    modal.style.display = 'block';
    
    // Close modal when clicking outside of it
    modal.onclick = function(event) {
        if (event.target === modal) {
            closeCandidateModal();
        }
    };
}

// Close candidate details modal
function closeCandidateModal() {
    const modal = document.getElementById('candidate-modal');
    modal.style.display = 'none';
}

// Show no more cards message
async function showNoMoreCards() {
    const container = document.getElementById('card-container');
    container.innerHTML = '';
    
    // Hide action buttons when no more cards
    const actionButtons = document.querySelector('.action-buttons');
    if (actionButtons) {
        actionButtons.style.display = 'none';
    }
    
    // Determine what message to show based on current state
    try {
        // Check if we have any processing candidates
        const processingResponse = await fetch('/api/candidates/processing');
        const processingCandidates = await processingResponse.json();
        
        // Check total candidates we've seen
        const hasReviewedCandidates = stats.reviewed > 0;
        const isProcessing = processingCandidates.length > 0;
        
        const noMoreCardsElement = document.getElementById('no-more-cards');
        
        if (isProcessing) {
            // Candidates are still being processed
            noMoreCardsElement.innerHTML = `
                <h2>Analyzing Candidates...</h2>
                <p>We're analyzing ${processingCandidates.length} candidates. New ones will appear automatically when ready!</p>
                <div class="processing-indicator">
                    <div class="spinner"></div>
                    <span>Processing in progress...</span>
                </div>
            `;
            // Start real-time updates if not already running
            if (!realTimeUpdateInterval) {
                startRealTimeUpdates();
            }
        } else if (!hasReviewedCandidates && candidates.length === 0) {
            // No candidates at all - initial state
            noMoreCardsElement.innerHTML = `
                <h2>Ready to Review Candidates</h2>
                <p>Add candidate resumes to the candidates/ folder and refresh the page to start reviewing!</p>
                <button onclick="window.location.reload()">Refresh</button>
            `;
        } else {
            // Actually finished reviewing all candidates
            noMoreCardsElement.innerHTML = `
                <h2>No More Candidates</h2>
                <p>You've reviewed all available candidates!</p>
                <button onclick="window.location.reload()">Refresh</button>
            `;
        }
        
        noMoreCardsElement.style.display = 'block';
        
    } catch (error) {
        console.error('Error determining no-more-cards state:', error);
        // Fallback to original message
        const noMoreCardsElement = document.getElementById('no-more-cards');
        noMoreCardsElement.innerHTML = `
            <h2>No More Candidates</h2>
            <p>You've reviewed all available candidates!</p>
            <button onclick="window.location.reload()">Refresh</button>
        `;
        noMoreCardsElement.style.display = 'block';
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
    if (confirm('Are you sure you want to restart? This will clear all saved and passed candidates and return you to the job description screen.')) {
        restartSession();
    }
}

async function restartSession() {
    try {
        await fetch('/api/restart', { method: 'POST' });
        
        // Reset processing tracking state
        window.wasProcessing = false;
        window.hasShownCompleted = false;
        hasShownProcessingNotification = false;
        
        // Set flag to show job description screen
        window.showJobDescriptionScreen = true;
        
        // Reset UI state
        currentIndex = 0;
        candidates = [];
        stats = {
            reviewed: 0,
            saved: 0,
            starred: 0,
            passed: 0,
            leftToReview: 0,
            failed: 0
        };
        updateStats();
        
        // Clear saved candidates display
        document.getElementById('saved-candidates').innerHTML = '<div class="empty-message">No saved candidates yet.</div>';
        
        // Show job description screen
        checkJobDescription();
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

// Processing status updates with real-time features
function startProcessingStatusUpdates() {
    console.log('🚀 Starting real-time processing status updates');
    updateProcessingStatus();
    setInterval(updateProcessingStatus, 3000);
}

// Processing status updates with real-time features  
async function updateProcessingStatus() {
    try {
        // Try to get detailed processing stats first
        const statsResponse = await fetch('/api/process/stats');
        const stats = await statsResponse.json();
        
        // Get standard status for comparison
        const statusResponse = await fetch('/api/process/status');
        const status = await statusResponse.json();
        
        // Update status text
        const statusElement = document.getElementById('processing-status');
        const progressElement = document.getElementById('processing-progress');
        const progressBar = document.getElementById('progress-bar');
        const progressFill = document.getElementById('progress-fill');
        
        if (status.is_processing) {
            window.hasShownCompleted = false;
            
            statusElement.textContent = 'Processing...';
            progressElement.textContent = `${status.processed_count}/${status.total_count} candidates (${Math.round(status.progress)}%)`;
            progressBar.style.display = 'block';
            progressFill.style.width = status.progress + '%';
            
            // Show retry queue information
            if (status.retry_queues) {
                const retryInfo = [];
                if (status.retry_queues.quick_retry > 0) {
                    retryInfo.push(`${status.retry_queues.quick_retry} quick retry`);
                }
                if (status.retry_queues.long_retry > 0) {
                    retryInfo.push(`${status.retry_queues.long_retry} long retry`);
                }
                if (status.retry_queues.failed > 0) {
                    retryInfo.push(`${status.retry_queues.failed} failed`);
                }
                
                if (retryInfo.length > 0) {
                    progressElement.textContent += ` | Retry: ${retryInfo.join(', ')}`;
                }
            }
        } else {
            if (status.status === 'completed' && !window.hasShownCompleted) {
                window.hasShownCompleted = true;
                statusElement.textContent = 'Completed';
                progressElement.textContent = 'All candidates analyzed';
                
                // Show failed candidates info if any
                if (status.retry_queues && status.retry_queues.failed > 0) {
                    showNotification(`Processing completed. ${status.retry_queues.failed} candidates failed after max retries.`, 'warning');
                }
                
                setTimeout(() => {
                    statusElement.textContent = 'Idle';
                    progressElement.textContent = '';
                }, 3000);
            } else if (status.status === 'error') {
                statusElement.textContent = 'Error';
                progressElement.textContent = 'Processing failed';
            } else if (status.status === 'idle' || !window.hasShownCompleted) {
                if (statusElement.textContent !== 'Completed') {
                    statusElement.textContent = 'Idle';
                    progressElement.textContent = '';
                }
            }
            progressBar.style.display = 'none';
            progressFill.style.width = '0%';
        }
        
        // Track processing state changes
        if (!window.wasProcessing) {
            window.wasProcessing = status.is_processing;
        }
        
        // If processing just completed
        if (!status.is_processing && window.wasProcessing) {
            window.wasProcessing = false;
            hasShownProcessingNotification = false;
            showNotification('All candidates have been analyzed!', 'success');
        }
        
        // Show failed candidates info and update stats
        try {
            const failedResponse = await fetch('/api/process/failed');
            const failedCandidates = await failedResponse.json();
            
            // Update failed count in stats
            stats.failed = failedCandidates.length;
            updateStats();
            
            if (failedCandidates.length > 0) {
                const failedElement = document.getElementById('failed-candidates-info');
                if (failedElement) {
                    failedElement.textContent = `${failedCandidates.length} candidates failed processing`;
                    failedElement.style.display = 'block';
                }
            }
        } catch (failedError) {
            // Failed candidates info is optional
            console.log('Failed candidates info not available');
        }
        
    } catch (error) {
        console.error('Error updating processing status:', error);
        // Fallback: try basic status update
        try {
            const response = await fetch('/api/process/status');
            const status = await response.json();
            
            const statusElement = document.getElementById('processing-status');
            const progressElement = document.getElementById('processing-progress');
            
            if (status.is_processing) {
                statusElement.textContent = 'Processing...';
                progressElement.textContent = `${status.processed_count}/${status.total_count} candidates`;
            } else {
                statusElement.textContent = status.status || 'Idle';
                progressElement.textContent = '';
            }
        } catch (fallbackError) {
            console.error('Fallback status update also failed:', fallbackError);
        }
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

// Export candidates to Excel
async function exportCandidates() {
    const exportBtn = document.querySelector('.export-btn');
    
    // Check if there are any saved candidates first
    try {
        const response = await fetch('/api/saved');
        const savedCandidates = await response.json();
        
        if (savedCandidates.length === 0) {
            alert('No candidates to export. Save some candidates first!');
            return;
        }
        
        // Disable button and show loading state
        exportBtn.disabled = true;
        exportBtn.innerHTML = '<span class="btn-icon">⏳</span> Exporting...';
        
        // Call export API
        const exportResponse = await fetch('/api/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (exportResponse.ok) {
            // Get the blob and download it
            const blob = await exportResponse.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'shortlisted_candidates.xlsx';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const error = await exportResponse.json();
            alert(error.error || 'Failed to export candidates');
        }
        
    } catch (error) {
        console.error('Error exporting candidates:', error);
        alert('Error exporting candidates. Please try again.');
    } finally {
        // Reset button state
        exportBtn.disabled = false;
        exportBtn.innerHTML = '<span class="btn-icon">📊</span> Export to Excel';
    }
} 

// Export failed candidates to Excel
async function exportFailedCandidates() {
    try {
        // Check if there are any failed candidates first
        const response = await fetch('/api/process/failed');
        const failedCandidates = await response.json();
        
        if (failedCandidates.length === 0) {
            alert('No failed candidates to export.');
            return;
        }
        
        // Call export API
        const exportResponse = await fetch('/api/export-failed', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (exportResponse.ok) {
            // Get the blob and download it
            const blob = await exportResponse.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'failed_candidates.xlsx';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showNotification(`Downloaded ${failedCandidates.length} failed candidates to Excel file`, 'success');
        } else {
            const error = await exportResponse.json();
            alert(error.error || 'Failed to export failed candidates');
        }
        
    } catch (error) {
        console.error('Error exporting failed candidates:', error);
        alert('Error exporting failed candidates. Please try again.');
    }
}

// Show notification toast
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add to body
    document.body.appendChild(notification);
    
    // Trigger animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 5000);
}

// Right panel tab switching functionality
function switchRightTab(tabName) {
    // Update active tab
    document.querySelectorAll('.right-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.getElementById(`${tabName}-right-tab`).classList.add('active');
    
    // Show corresponding content
    document.querySelectorAll('.right-tab-content').forEach(content => {
        content.classList.remove('active');
        content.style.display = 'none';
    });
    document.getElementById(`${tabName}-content`).classList.add('active');
    document.getElementById(`${tabName}-content`).style.display = 'block';
    
    // Load data for the selected tab
    if (tabName === 'passed') {
        loadPassedCandidatesForRightPanel();
    }
}

// Load passed candidates for right panel
async function loadPassedCandidatesForRightPanel() {
    try {
        const response = await fetch('/api/passed');
        const candidates = await response.json();
        passedCandidates = candidates;
        
        updatePassedCount(candidates.length);
        displayPassedCandidatesInRightPanel(candidates);
    } catch (error) {
        console.error('Error loading passed candidates:', error);
        showNotification('Error loading passed candidates', 'error');
    }
}

// Display passed candidates in right panel format (matching saved candidates style)
function displayPassedCandidatesInRightPanel(candidates) {
    const container = document.getElementById('passed-candidates');
    container.innerHTML = '';
    
    // Store in global array for modal access
    passedCandidates = candidates;
    
    if (candidates.length === 0) {
        container.innerHTML = '<p class="empty-message">No passed candidates yet</p>';
        return;
    }
    
    candidates.forEach((candidate, index) => {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'saved-card'; // Use same class as saved candidates
        cardDiv.innerHTML = `
            <div class="saved-card-content">
                <h4 class="saved-name">${candidate.nickname || 'Anonymous Pro'}</h4>
                <div class="saved-experience">Passed ${formatTimestamp(candidate.passed_at)}</div>
                <div class="candidate-actions">
                    <button class="action-btn view-btn-subtle" onclick="viewCandidateFromPanel('${candidate.id}', 'passed')">View</button>
                    <button class="action-btn star-btn-subtle" onclick="modifyDecision('${candidate.id}', 'star')">Star</button>
                    <button class="action-btn save-btn-subtle" onclick="modifyDecision('${candidate.id}', 'save')">Save</button>
                </div>
            </div>
        `;
        container.appendChild(cardDiv);
    });
}



// Modify candidate decision
async function modifyDecision(candidateId, newDecision) {
    try {
        const response = await fetch('/api/modify-decision', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                candidate_id: candidateId,
                new_decision: newDecision
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            let message = '';
            if (newDecision === 'unreviewed') {
                message = 'Candidate moved back to review queue';
            } else if (newDecision === 'save') {
                // Check if this was an unstar action (old decision was star)
                if (result.old_decision === 'star') {
                    message = 'Candidate unstarred successfully';
                } else {
                    message = 'Candidate saved successfully';
                }
            } else if (newDecision === 'star') {
                message = 'Candidate starred successfully';
            } else if (newDecision === 'pass') {
                message = 'Candidate moved to passed list';
            }
            
            showNotification(message, 'success');
            
            // Refresh right panel if passed tab is active
            const passedTab = document.getElementById('passed-right-tab');
            if (passedTab && passedTab.classList.contains('active')) {
                loadPassedCandidatesForRightPanel();
            }
            
            // Update counts and reload data for other views
            loadSavedCandidates(); // Updates the saved candidates in right panel
            updateRightTabCounts();
            
            // If moved back to review, reload candidates
            if (newDecision === 'unreviewed') {
                loadCandidates();
            }
        } else {
            showNotification(result.message || 'Error modifying decision', 'error');
        }
    } catch (error) {
        console.error('Error modifying decision:', error);
        showNotification('Error modifying decision', 'error');
    }
}

// Update right panel tab counts
async function updateRightTabCounts() {
    try {
        // Update saved count
        const savedResponse = await fetch('/api/saved');
        const savedData = await savedResponse.json();
        updateSavedCount(savedData.length);
        
        // Update passed count
        const passedResponse = await fetch('/api/passed');
        const passedData = await passedResponse.json();
        updatePassedCount(passedData.length);
        
    } catch (error) {
        console.error('Error updating tab counts:', error);
    }
}

// Update saved count in right panel tab
function updateSavedCount(count) {
    const savedCountElement = document.getElementById('saved-tab-count');
    if (savedCountElement) {
        savedCountElement.textContent = count;
    }
}

// Update passed count in right panel tab
function updatePassedCount(count) {
    const passedCountElement = document.getElementById('passed-tab-count');
    if (passedCountElement) {
        passedCountElement.textContent = count;
    }
}

// Format timestamp for display
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
}

// View candidate from right panel
function viewCandidateFromPanel(candidateId, type) {
    let candidate = null;
    
    if (type === 'saved') {
        candidate = savedCandidates.find(c => c.id === candidateId);
    } else if (type === 'passed') {
        candidate = passedCandidates.find(c => c.id === candidateId);
    }
    
    if (candidate) {
        openCandidateModal(candidate);
    } else {
        console.error('Candidate not found:', candidateId, type);
        showNotification('Error loading candidate details', 'error');
    }
}

// Initialize right panel tab counts on startup
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        updateRightTabCounts();
    }, 1000); // Wait a bit for the main initialization to complete
});