/**
 * Telegram Mini App - Video Rewards
 * Main Application Logic
 */

// API Configuration
const API_BASE_URL = window.location.origin;

// Telegram WebApp
const tg = window.Telegram?.WebApp;

// App State
const state = {
    user: null,
    videos: [],
    currentVideo: null,
    referralStats: null
};

// DOM Elements
const elements = {
    userName: document.getElementById('userName'),
    userAvatar: document.getElementById('userAvatar'),
    starsCount: document.getElementById('starsCount'),
    progressText: document.getElementById('progressText'),
    progressFill: document.getElementById('progressFill'),
    discountBanner: document.getElementById('discountBanner'),
    discountProgress: document.getElementById('discountProgress'),
    claimDiscountBtn: document.getElementById('claimDiscountBtn'),
    videosList: document.getElementById('videosList'),
    videoModal: document.getElementById('videoModal'),
    videoPlayer: document.getElementById('videoPlayer'),
    videoTitle: document.getElementById('videoTitle'),
    videoProgressFill: document.getElementById('videoProgressFill'),
    watchProgress: document.getElementById('watchProgress'),
    closeModal: document.getElementById('closeModal'),
    subscribeBtn: document.getElementById('subscribeBtn'),
    subscribeTask: document.getElementById('subscribeTask'),
    inviteBtn: document.getElementById('inviteBtn'),
    referralModal: document.getElementById('referralModal'),
    closeReferralModal: document.getElementById('closeReferralModal'),
    referralLink: document.getElementById('referralLink'),
    referralCount: document.getElementById('referralCount'),
    referralEarned: document.getElementById('referralEarned'),
    copyLinkBtn: document.getElementById('copyLinkBtn'),
    shareBtn: document.getElementById('shareBtn'),
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage')
};

// Initialize App
async function init() {
    // Initialize Telegram WebApp
    if (tg) {
        tg.ready();
        tg.expand();

        // Apply Telegram theme
        applyTelegramTheme();
    }

    // Get user data
    const userData = getTelegramUserData();

    // Authenticate user
    await authenticateUser(userData);

    // Load videos
    await loadVideos();

    // Setup event listeners
    setupEventListeners();
}

// Apply Telegram Theme Colors
function applyTelegramTheme() {
    if (!tg?.themeParams) return;

    const root = document.documentElement;
    const theme = tg.themeParams;

    if (theme.bg_color) root.style.setProperty('--tg-theme-bg-color', theme.bg_color);
    if (theme.text_color) root.style.setProperty('--tg-theme-text-color', theme.text_color);
    if (theme.hint_color) root.style.setProperty('--tg-theme-hint-color', theme.hint_color);
    if (theme.link_color) root.style.setProperty('--tg-theme-link-color', theme.link_color);
    if (theme.button_color) root.style.setProperty('--tg-theme-button-color', theme.button_color);
    if (theme.button_text_color) root.style.setProperty('--tg-theme-button-text-color', theme.button_text_color);
    if (theme.secondary_bg_color) root.style.setProperty('--tg-theme-secondary-bg-color', theme.secondary_bg_color);
}

// Get Telegram User Data
function getTelegramUserData() {
    // Check for startapp parameter (referral code)
    const startParam = tg?.initDataUnsafe?.start_param || getUrlParam('startapp');

    if (tg?.initDataUnsafe?.user) {
        const user = tg.initDataUnsafe.user;
        return {
            telegram_id: user.id,
            username: user.username,
            first_name: user.first_name,
            last_name: user.last_name,
            referral_code: startParam
        };
    }

    // Fallback for development
    return {
        telegram_id: Math.floor(Math.random() * 1000000) + 100000,
        username: 'test_user',
        first_name: 'Test',
        last_name: 'User',
        referral_code: startParam
    };
}

// Get URL Parameter
function getUrlParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

// API Request Helper
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    // Add Telegram init data for validation
    if (tg?.initData) {
        headers['X-Telegram-Init-Data'] = tg.initData;
    }

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API Error');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Authenticate User
async function authenticateUser(userData) {
    try {
        state.user = await apiRequest('/api/auth', {
            method: 'POST',
            body: JSON.stringify(userData)
        });

        updateUI();
    } catch (error) {
        console.error('Auth error:', error);
        showToast('Ошибка авторизации', 'error');
    }
}

// Load Videos
async function loadVideos() {
    if (!state.user) return;

    try {
        state.videos = await apiRequest(`/api/videos?telegram_id=${state.user.telegram_id}`);
        renderVideos();
    } catch (error) {
        console.error('Videos load error:', error);
        elements.videosList.innerHTML = '<div class="loading">Ошибка загрузки видео</div>';
    }
}

// Update UI
function updateUI() {
    if (!state.user) return;

    // User info
    elements.userName.textContent = state.user.first_name || state.user.username || 'Пользователь';
    elements.userAvatar.textContent = (state.user.first_name || 'U')[0].toUpperCase();
    elements.starsCount.textContent = state.user.stars;

    // Progress
    const progress = Math.min((state.user.stars / 3) * 100, 100);
    elements.progressText.textContent = `${state.user.stars}/3 ⭐`;
    elements.progressFill.style.width = `${progress}%`;

    // Discount banner
    if (state.user.discount_available) {
        elements.discountBanner.classList.remove('hidden');
        elements.discountProgress.classList.add('hidden');
    } else if (state.user.discount_claimed) {
        elements.discountBanner.classList.add('hidden');
        elements.discountProgress.classList.add('hidden');
    } else {
        elements.discountBanner.classList.add('hidden');
        elements.discountProgress.classList.remove('hidden');
    }

    // Subscribe task
    if (state.user.subscription_reward_claimed) {
        elements.subscribeTask.classList.add('task-completed');
        elements.subscribeBtn.textContent = 'Выполнено';
        elements.subscribeBtn.disabled = true;
    }
}

// Render Videos
function renderVideos() {
    if (!state.videos.length) {
        elements.videosList.innerHTML = '<div class="loading">Нет доступных видео</div>';
        return;
    }

    elements.videosList.innerHTML = state.videos.map(video => `
        <div class="video-card" data-video-id="${video.id}">
            <div class="video-thumbnail">
                ${video.thumbnail_url ? `<img src="${video.thumbnail_url}" alt="${video.title}">` : ''}
                <div class="play-button">▶</div>
                ${getVideoStatus(video)}
            </div>
            <div class="video-details">
                <h3>${video.title}</h3>
                <p>${video.description || ''}</p>
                <div class="video-meta">
                    <span>${formatDuration(video.duration_seconds)}</span>
                    <span class="video-reward">⭐ +${video.reward_stars}</span>
                </div>
            </div>
        </div>
    `).join('');

    // Add click handlers
    document.querySelectorAll('.video-card').forEach(card => {
        card.addEventListener('click', () => {
            const videoId = parseInt(card.dataset.videoId);
            openVideo(videoId);
        });
    });
}

// Get Video Status Badge
function getVideoStatus(video) {
    if (video.reward_claimed) {
        return '<span class="video-status watched">✓ Просмотрено</span>';
    }
    if (video.watch_progress > 0) {
        return `<span class="video-status reward">${video.watch_progress}%</span>`;
    }
    return '<span class="video-status new">Новое</span>';
}

// Format Duration
function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Open Video Player
function openVideo(videoId) {
    const video = state.videos.find(v => v.id === videoId);
    if (!video) return;

    state.currentVideo = video;

    elements.videoTitle.textContent = video.title;
    elements.videoPlayer.src = video.video_url;
    elements.videoProgressFill.style.width = '0%';
    elements.watchProgress.textContent = '0%';

    elements.videoModal.classList.remove('hidden');
    elements.videoPlayer.play();

    // Haptic feedback
    if (tg?.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }
}

// Close Video Player
function closeVideo() {
    elements.videoPlayer.pause();
    elements.videoPlayer.src = '';
    elements.videoModal.classList.add('hidden');
    state.currentVideo = null;
}

// Update Video Progress
async function updateVideoProgress(progress) {
    if (!state.currentVideo || !state.user) return;

    const roundedProgress = Math.floor(progress);

    elements.videoProgressFill.style.width = `${roundedProgress}%`;
    elements.watchProgress.textContent = `${roundedProgress}%`;

    // Send progress to server every 10%
    if (roundedProgress % 10 === 0 || roundedProgress >= 80) {
        try {
            const result = await apiRequest(`/api/video/progress?telegram_id=${state.user.telegram_id}`, {
                method: 'POST',
                body: JSON.stringify({
                    video_id: state.currentVideo.id,
                    progress: roundedProgress
                })
            });

            if (result.stars_earned > 0) {
                state.user.stars = result.total_stars;
                state.user.discount_available = result.discount_available;
                updateUI();
                showToast(`+${result.stars_earned} звезда!`);

                // Update video status
                const videoIndex = state.videos.findIndex(v => v.id === state.currentVideo.id);
                if (videoIndex !== -1) {
                    state.videos[videoIndex].reward_claimed = true;
                    state.videos[videoIndex].is_watched = true;
                    renderVideos();
                }

                // Haptic feedback
                if (tg?.HapticFeedback) {
                    tg.HapticFeedback.notificationOccurred('success');
                }
            }
        } catch (error) {
            console.error('Progress update error:', error);
        }
    }
}

// Check Subscription
async function checkSubscription() {
    if (!state.user) return;

    // Open channel in Telegram
    const channelUrl = 'https://t.me/YOUR_CHANNEL'; // Replace with actual channel
    window.open(channelUrl, '_blank');

    // Show instructions
    setTimeout(async () => {
        try {
            const result = await apiRequest(`/api/subscribe/check?telegram_id=${state.user.telegram_id}`, {
                method: 'POST'
            });

            if (result.stars_earned > 0) {
                state.user.stars = result.total_stars;
                state.user.is_subscribed = result.is_subscribed;
                state.user.subscription_reward_claimed = true;
                state.user.discount_available = result.discount_available;
                updateUI();
                showToast(`+${result.stars_earned} звезда за подписку!`);

                if (tg?.HapticFeedback) {
                    tg.HapticFeedback.notificationOccurred('success');
                }
            }
        } catch (error) {
            console.error('Subscription check error:', error);
        }
    }, 3000);
}

// Open Referral Modal
async function openReferralModal() {
    if (!state.user) return;

    try {
        state.referralStats = await apiRequest(`/api/referral/stats?telegram_id=${state.user.telegram_id}`);

        elements.referralCount.textContent = state.referralStats.referral_count;
        elements.referralEarned.textContent = state.referralStats.referral_count;
        elements.referralLink.value = state.referralStats.referral_link;

        elements.referralModal.classList.remove('hidden');
    } catch (error) {
        console.error('Referral stats error:', error);
    }
}

// Copy Referral Link
function copyReferralLink() {
    if (!state.referralStats) return;

    navigator.clipboard.writeText(state.referralStats.referral_link)
        .then(() => {
            showToast('Ссылка скопирована!');
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
        })
        .catch(() => {
            // Fallback
            elements.referralLink.select();
            document.execCommand('copy');
            showToast('Ссылка скопирована!');
        });
}

// Share Referral Link
function shareReferralLink() {
    if (!state.referralStats) return;

    const text = `Смотри видео и получай скидку 60 000 рублей! Присоединяйся по моей ссылке:`;

    if (tg?.openTelegramLink) {
        // Use Telegram share
        const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(state.referralStats.referral_link)}&text=${encodeURIComponent(text)}`;
        tg.openTelegramLink(shareUrl);
    } else if (navigator.share) {
        // Use Web Share API
        navigator.share({
            title: 'Video Rewards',
            text: text,
            url: state.referralStats.referral_link
        });
    } else {
        copyReferralLink();
    }
}

// Claim Discount
async function claimDiscount() {
    if (!state.user || !state.user.discount_available) return;

    try {
        const result = await apiRequest(`/api/discount/claim?telegram_id=${state.user.telegram_id}`, {
            method: 'POST'
        });

        if (result.success) {
            state.user.discount_claimed = true;
            state.user.discount_available = false;
            updateUI();

            // Show discount code
            alert(`${result.message}\n\nВаш код скидки: ${result.discount_code}`);

            if (tg?.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
        }
    } catch (error) {
        console.error('Claim discount error:', error);
        showToast('Ошибка получения скидки', 'error');
    }
}

// Show Toast
function showToast(message, type = 'success') {
    elements.toastMessage.textContent = message;
    elements.toast.style.background = type === 'error' ? '#ff3b30' : '#34c759';
    elements.toast.classList.remove('hidden');

    setTimeout(() => {
        elements.toast.classList.add('hidden');
    }, 3000);
}

// Setup Event Listeners
function setupEventListeners() {
    // Video player events
    elements.videoPlayer.addEventListener('timeupdate', () => {
        if (elements.videoPlayer.duration) {
            const progress = (elements.videoPlayer.currentTime / elements.videoPlayer.duration) * 100;
            updateVideoProgress(progress);
        }
    });

    elements.closeModal.addEventListener('click', closeVideo);
    elements.videoModal.addEventListener('click', (e) => {
        if (e.target === elements.videoModal) closeVideo();
    });

    // Subscribe button
    elements.subscribeBtn.addEventListener('click', checkSubscription);

    // Invite button
    elements.inviteBtn.addEventListener('click', openReferralModal);

    // Referral modal
    elements.closeReferralModal.addEventListener('click', () => {
        elements.referralModal.classList.add('hidden');
    });
    elements.referralModal.addEventListener('click', (e) => {
        if (e.target === elements.referralModal) {
            elements.referralModal.classList.add('hidden');
        }
    });
    elements.copyLinkBtn.addEventListener('click', copyReferralLink);
    elements.shareBtn.addEventListener('click', shareReferralLink);

    // Discount claim
    elements.claimDiscountBtn.addEventListener('click', claimDiscount);

    // Handle back button in Telegram
    if (tg?.BackButton) {
        tg.BackButton.onClick(() => {
            if (!elements.videoModal.classList.contains('hidden')) {
                closeVideo();
            } else if (!elements.referralModal.classList.contains('hidden')) {
                elements.referralModal.classList.add('hidden');
            } else {
                tg.close();
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
