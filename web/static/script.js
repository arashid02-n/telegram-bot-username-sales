// ==========================================
// CATEGORY FILTER & MODAL CONTROLLER
// ==========================================

const modal = document.getElementById('offerModal');
const displayHandle = document.getElementById('targetBotDisplay');
const hiddenInput = document.getElementById('targetBotInput');

document.addEventListener('DOMContentLoaded', () => {
  setupCategoryFilters();
  setupBackToTop();
});

// --- 1. BOT CARDS ---
// The cards are already in the page HTML (rendered on the server from
// bots.json), so search engines can read them. Nothing to load here.

// --- 2. INTERACTIVE CATEGORY FILTERING ---
function setupCategoryFilters() {
  const filterButtons = document.querySelectorAll('.filter-btn');
  const cards = document.querySelectorAll('.asset-card');
  const noResults = document.getElementById('noResults');

  filterButtons.forEach(button => {
    button.addEventListener('click', () => {
      // Toggle active class on buttons
      filterButtons.forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');

      const selectedCategory = button.getAttribute('data-filter');
      let shown = 0;
      cards.forEach(card => {
        card.hidden = selectedCategory !== 'all' && card.dataset.category !== selectedCategory;
        if (!card.hidden) shown++;
      });
      if (noResults) noResults.hidden = shown > 0;
    });
  });
}

// --- 3. MODAL CONTROLLER LOGIC ---
function openOfferModal(botUsername, minBid) {
  const formattedHandle = botUsername.startsWith('@') ? botUsername : `@${botUsername}`;
  displayHandle.textContent = formattedHandle;
  hiddenInput.value = botUsername;
  // Each listing has its own minimum offer (the "Minimum Offer" on its page).
  const bidField = document.getElementById('bidAmount');
  if (bidField && minBid) {
    bidField.min = minBid;
    bidField.placeholder = `e.g., ${minBid}`;
  }
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

  // 3. Extra safeguard: at least this listing's minimum (set by openOfferModal)
  const minBid = Number(document.getElementById('bidAmount').min) || 1;
  if (Number(bidInput) < minBid) {
    alert(`⚠️ Offer amount must be at least $${minBid}.`);
    document.getElementById('bidAmount').focus();
    return;
  }

  const offerData = {
    bot_username: formData.get('bot_username'),
    name: formData.get('name'),
    contact: contactInput,
    bid: bidInput,
    notes: formData.get('notes') || null,
    hp_field: formData.get('hp_field') || null  // honeypot, empty for humans
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

    // Some error responses are plain text, not JSON (e.g. 429), so don't let
    // parsing fail before we can look at the status code.
    let result = {};
    try {
      result = await response.json();
    } catch (parseError) {
      result = {};
    }

    if (!response.ok) {
      const err = new Error(typeof result.detail === 'string' ? result.detail : 'Server responded with an error.');
      err.status = response.status;
      throw err;
    }

    // 5. Success! Notify user and reset
    alert(`Thank you, ${offerData.name}! Your offer of $${offerData.bid} for ${offerData.bot_username} has been sent directly to our brokers.`);
    formElement.reset();
    
    if (typeof closeOfferModal === 'function') {
      closeOfferModal();
    }

  } catch (error) {
    console.error("Submission Error:", error);
    if (error.status === 429) {
      alert("⚠️ You've sent several offers in a short time. Please wait an hour, or message us directly on Telegram.");
    } else if (error.status === 422) {
      alert("⚠️ Please check your details: your name, a valid email / phone / @Telegram username, and an offer between this username's minimum and $1,000,000.");
    } else {
      alert("⚠️ Could not send your offer at this time. Please try contacting us directly via Telegram.");
    }
  } finally {
    // Restore button state
    submitBtn.textContent = originalBtnText;
    submitBtn.disabled = false;
  }
}

// Guide Modal Handling
const guideModal = document.getElementById('guideModal');

function openGuideModal() {
  if (guideModal) guideModal.showModal();
}

function closeGuideModal() {
  if (guideModal) guideModal.close();
}

// --- 4. BACK TO TOP BUTTON CONTROLLER ---
function setupBackToTop() {
  const backToTopBtn = document.getElementById('backToTopBtn');
  if (!backToTopBtn) return;

  const SCROLL_THRESHOLD = 300; // Shows button after scrolling down 300px

  const toggleButtonVisibility = () => {
    if (window.scrollY > SCROLL_THRESHOLD) {
      backToTopBtn.classList.add('visible');
    } else {
      backToTopBtn.classList.remove('visible');
    }
  };

  // Check scroll position on load
  toggleButtonVisibility();

  // Passive scroll listener for smooth performance
  window.addEventListener('scroll', toggleButtonVisibility, { passive: true });

  // Scroll smoothly to top on click
  backToTopBtn.addEventListener('click', (e) => {
    e.preventDefault(); // Prevents any default instant jump
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });
}

// About Modal Handling
const aboutModal = document.getElementById('aboutModal');

function openAboutModal() {
  if (aboutModal) aboutModal.showModal();
}

function closeAboutModal() {
  if (aboutModal) aboutModal.close();
}
