// ==========================================
// DYNAMIC BOT LOADER & MODAL CONTROLLER
// ==========================================

let allBotsData = []; // Store loaded bots globally for filtering

const modal = document.getElementById('offerModal');
const displayHandle = document.getElementById('targetBotDisplay');
const hiddenInput = document.getElementById('targetBotInput');
const assetGrid = document.getElementById('assetGrid');

// --- 1. FETCH & RENDER BOTS FROM JSON ---
document.addEventListener('DOMContentLoaded', () => {
  loadBotInventory();
  setupCategoryFilters();
});

async function loadBotInventory() {
  try {
    const response = await fetch('bots.json');
    if (!response.ok) throw new Error('Could not load bots.json');
    
    allBotsData = await response.json();
    renderBotCards(allBotsData);
  } catch (error) {
    console.error('Error loading bot inventory:', error);
    if (assetGrid) {
      assetGrid.innerHTML = `<p style="color: var(--text-muted); grid-column: 1/-1; text-align: center;">Unable to load inventory. Please refresh the page.</p>`;
    }
  }
}

function renderBotCards(bots) {
  if (!assetGrid) return;
  
  // Clear existing content
  assetGrid.innerHTML = '';

  if (bots.length === 0) {
    assetGrid.innerHTML = `<p style="color: var(--text-muted); grid-column: 1/-1; text-align: center;">No bot handles found in this category.</p>`;
    return;
  }

  // Generate HTML for each bot card
  bots.forEach(bot => {
    const badgeClass = bot.status_code === 'active' ? 'status-active' : 'status-pending';
    
    const cardHTML = `
      <div class="asset-card" data-category="${bot.category}">
        <div class="card-top">
          <span class="category-tag">${bot.category}</span>
          <span class="status-badge ${badgeClass}">${bot.status}</span>
        </div>

        <h3 class="bot-handle">@${bot.username}</h3>
        <p class="bot-desc">${bot.desc}</p>

        <div class="card-meta">
          <div class="meta-item">
            <span class="meta-label">Est. Value</span>
            <span class="meta-value">${bot.est_value}</span>
          </div>
          <div class="meta-item text-right">
            <span class="meta-label">Transfer Method</span>
            <span class="meta-value">@BotFather</span>
          </div>
        </div>

        <div class="card-actions">
          <a href="https://t.me/${bot.username}?start=website" target="_blank" rel="noopener" class="btn-telegram">
            💬 Make Offer on Telegram
          </a>
          <button type="button" class="btn-webform-link" onclick="openOfferModal('${bot.username}')">
            or submit via Web Form
          </button>
        </div>
      </div>
    `;
    
    assetGrid.insertAdjacentHTML('beforeend', cardHTML);
  });
}

// --- 2. INTERACTIVE CATEGORY FILTERING ---
function setupCategoryFilters() {
  const filterButtons = document.querySelectorAll('.filter-btn');

  filterButtons.forEach(button => {
    button.addEventListener('click', () => {
      // Toggle active class on buttons
      filterButtons.forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');

      const selectedCategory = button.getAttribute('data-filter');

      if (selectedCategory === 'all') {
        renderBotCards(allBotsData);
      } else {
        const filteredBots = allBotsData.filter(bot => bot.category === selectedCategory);
        renderBotCards(filteredBots);
      }
    });
  });
}

// --- 3. MODAL CONTROLLER LOGIC ---
function openOfferModal(botUsername) {
  const formattedHandle = botUsername.startsWith('@') ? botUsername : `@${botUsername}`;
  displayHandle.textContent = formattedHandle;
  hiddenInput.value = botUsername;
  modal.showModal();
}

function closeOfferModal() {
  modal.close();
}

/**
 * Handles the form submission by sending data to the Python FastAPI backend.
 */
// Ensure offerModal reference exists if defined above this block
const offerModal = document.getElementById('offerModal');

async function handleFormSubmit(event) {
  event.preventDefault(); 
  
  const formElement = event.target;

  if (!formElement.checkValidity()) {
    formElement.reportValidity();
    return;
  }

  const submitBtn = formElement.querySelector('button[type="submit"]');
  const originalBtnText = submitBtn.textContent;

  // 1. Gather form data
  const formData = new FormData(formElement);
  const contactInput = formData.get('contact').trim();
  const bidInput = formData.get('bid');

  // 3. Optional: Extra safeguard for bid amount (ensures positive number >= 100)
  if (Number(bidInput) < 100) {
    alert("⚠️ Offer amount must be at least $100.");
    document.getElementById('bidAmount').focus();
    return;
  }

  const offerData = {
    bot_username: formData.get('bot_username'),
    name: formData.get('name'),
    contact: contactInput,
    bid: bidInput,
    notes: formData.get('notes') || null
  };

  try {
    // Show loading state on the button
    submitBtn.textContent = "Sending Offer...";
    submitBtn.disabled = true;

    // SMART URL ROUTER
    const isLocalDev = window.location.port === '3000' || 
                       window.location.port === '5500' || 
                       window.location.protocol === 'file:';
                       
    const apiUrl = isLocalDev ? 'http://127.0.0.1:8000/api/submit-form' : '/api/submit-form';

    // 4. Send the POST request
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(offerData)
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || 'Server responded with an error.');
    }

    // 5. Success! Notify user and reset
    alert(`Thank you, ${offerData.name}! Your offer of $${offerData.bid} for ${offerData.bot_username} has been sent directly to our brokers.`);
    formElement.reset();
    
    if (typeof closeOfferModal === 'function') {
      closeOfferModal();
    }

  } catch (error) {
    console.error("Submission Error:", error);
    alert("⚠️ Could not send your offer at this time. Please try contacting us directly via Telegram.");
  } finally {
    // Restore button state
    submitBtn.textContent = originalBtnText;
    submitBtn.disabled = false;
  }
}

// Light dismiss: Close modal if user clicks backdrop
if (modal) {
  modal.addEventListener('click', (event) => {
    const rect = modal.getBoundingClientRect();
    const isInDialog = (
      rect.top <= event.clientY &&
      event.clientY <= rect.top + rect.height &&
      rect.left <= event.clientX &&
      event.clientX <= rect.left + rect.width
    );
    if (!isInDialog && typeof closeOfferModal === 'function') {
      closeOfferModal();
    }
  });
}

// Guide Modal Handling
const guideModal = document.getElementById('guideModal');

function openGuideModal() {
  if (guideModal) guideModal.showModal();
}

function closeGuideModal() {
  if (guideModal) guideModal.close();
}

// Light dismiss for guide modal
if (guideModal) {
  guideModal.addEventListener('click', (event) => {
    const rect = guideModal.getBoundingClientRect();
    const isInDialog = (
      rect.top <= event.clientY &&
      event.clientY <= rect.top + rect.height &&
      rect.left <= event.clientX &&
      event.clientX <= rect.left + rect.width
    );
    if (!isInDialog) closeGuideModal();
  });
}