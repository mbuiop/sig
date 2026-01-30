/**
 * InstaSocial - Main JavaScript File
 * مدیریت کامل شبکه اجتماعی
 */

// Global Variables
let currentUser = 'user1';
let socket = null;
let currentChatUser = null;
let typingTimeout = null;
let currentPage = 'home';
let posts = [];
let stories = [];
let users = [];
let notifications = [];
let messages = [];
let isLoading = false;
let page = 1;
let hasMorePosts = true;

// Initialize Application
document.addEventListener('DOMContentLoaded', function() {
    initApplication();
});

function initApplication() {
    console.log('🚀 Initializing InstaSocial...');
    
    // Initialize current user
    initCurrentUser();
    
    // Setup event listeners
    setupEventListeners();
    
    // Connect to WebSocket
    connectToSocket();
    
    // Load initial data
    loadInitialData();
    
    // Setup navigation
    setupNavigation();
    
    console.log('✅ Application initialized successfully');
}

function initCurrentUser() {
    const usernameInput = document.getElementById('usernameInput');
    const currentUsernameSpan = document.getElementById('currentUsername');
    const profileUsername = document.getElementById('profileUsername');
    
    // Get saved username or use default
    const savedUsername = localStorage.getItem('instasocial_username');
    if (savedUsername) {
        currentUser = savedUsername;
        usernameInput.value = currentUser;
        currentUsernameSpan.textContent = currentUser;
        if (profileUsername) profileUsername.textContent = currentUser;
    }
    
    // Update username when changed
    usernameInput.addEventListener('change', function() {
        if (this.value.trim()) {
            currentUser = this.value.trim();
            localStorage.setItem('instasocial_username', currentUser);
            currentUsernameSpan.textContent = currentUser;
            if (profileUsername) profileUsername.textContent = currentUser;
            
            // Reconnect with new username
            reconnectWithNewUser();
            
            // Show notification
            showNotification(`نام کاربری تغییر کرد به: ${currentUser}`, 'info');
        }
    });
}

function reconnectWithNewUser() {
    // Disconnect existing socket
    if (socket) {
        socket.disconnect();
    }
    
    // Reload all data
    loadInitialData();
    
    // Reconnect socket
    connectToSocket();
}

function connectToSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('✅ Connected to WebSocket server');
        showNotification('اتصال برقرار شد', 'success');
        
        // Join user room
        socket.emit('join_user', { username: currentUser });
    });
    
    socket.on('disconnect', function() {
        console.log('❌ Disconnected from WebSocket server');
        showNotification('اتصال قطع شد', 'error');
    });
    
    socket.on('new_message', function(data) {
        console.log('📨 New message received:', data);
        handleNewMessage(data);
    });
    
    socket.on('user_typing', function(data) {
        console.log('⌨️  Typing indicator:', data);
        handleTypingIndicator(data);
    });
    
    socket.on('new_notification', function(data) {
        console.log('🔔 New notification:', data);
        handleNewNotification(data);
    });
    
    socket.on('new_post', function(data) {
        console.log('🆕 New post:', data);
        handleNewPost(data);
    });
    
    socket.on('error', function(data) {
        console.error('Socket error:', data);
        showNotification(`خطا: ${data.message}`, 'error');
    });
}

function loadInitialData() {
    console.log('📥 Loading initial data...');
    
    // Show loading state
    showLoading(true);
    
    // Load data in parallel
    Promise.all([
        loadPosts(),
        loadStories(),
        loadUsers(),
        loadNotifications(),
        loadMessages()
    ])
    .then(() => {
        console.log('✅ All data loaded successfully');
        showLoading(false);
    })
    .catch(error => {
        console.error('❌ Error loading data:', error);
        showNotification('خطا در بارگذاری اطلاعات', 'error');
        showLoading(false);
    });
}

function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.style.display = show ? 'block' : 'none';
    }
    isLoading = show;
}

async function loadPosts() {
    try {
        const response = await fetch(`/api/posts?page=${page}&username=${currentUser}`);
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        console.log('📄 Posts loaded:', data);
        
        if (data.success) {
            posts = data.posts || [];
            hasMorePosts = data.has_next || false;
            renderPosts();
        } else {
            throw new Error(data.error || 'Failed to load posts');
        }
    } catch (error) {
        console.error('Error loading posts:', error);
        showNotification('خطا در بارگذاری پست‌ها', 'error');
    }
}

async function loadStories() {
    try {
        const response = await fetch('/api/stories');
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        console.log('📖 Stories loaded:', data);
        
        if (data.success) {
            stories = data.stories || [];
            renderStories();
        }
    } catch (error) {
        console.error('Error loading stories:', error);
    }
}

async function loadUsers() {
    try {
        const response = await fetch(`/api/chats/users?username=${currentUser}`);
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        console.log('👥 Users loaded:', data);
        
        if (data.success) {
            users = data.users || [];
            renderSuggestions();
        }
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

async function loadNotifications() {
    try {
        // This would normally be an API call
        // For now, use mock data
        notifications = [
            { id: 1, type: 'like', user: 'user2', post_id: 1, time: '5 دقیقه پیش' },
            { id: 2, type: 'comment', user: 'user3', post_id: 1, text: 'عالی!', time: '10 دقیقه پیش' },
            { id: 3, type: 'follow', user: 'test', time: '1 ساعت پیش' }
        ];
        
        updateNotificationBadge();
        renderNotifications();
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

async function loadMessages() {
    try {
        // This would normally be an API call
        // For now, use mock data
        messages = [
            { id: 1, user: 'user2', last_message: 'سلام چطوری؟', time: '5 دقیقه پیش', unread: true },
            { id: 2, user: 'user3', last_message: 'پست خوبی بود', time: '1 ساعت پیش', unread: false },
            { id: 3, user: 'admin', last_message: 'خوش آمدید', time: '2 ساعت پیش', unread: true }
        ];
        
        updateMessageBadge();
        renderMessages();
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

function renderPosts() {
    const feedContainer = document.getElementById('feedContainer');
    if (!feedContainer) return;
    
    if (posts.length === 0) {
        feedContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-camera" style="font-size: 64px; color: var(--text-secondary); margin-bottom: 20px;"></i>
                <h3>هنوز پستی وجود ندارد</h3>
                <p>اولین نفر باشید که پست می‌گذارد!</p>
                <button class="btn-primary" id="createFirstPostBtn" style="margin-top: 20px;">
                    <i class="fas fa-plus"></i>
                    ایجاد اولین پست
                </button>
            </div>
        `;
        
        document.getElementById('createFirstPostBtn')?.addEventListener('click', openCreatePostModal);
        return;
    }
    
    let html = '';
    posts.forEach(post => {
        const timeAgo = formatTimeAgo(new Date(post.created_at));
        
        html += `
        <div class="post-card" data-post-id="${post.id}">
            <div class="post-header">
                <div class="post-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <div class="post-user-info">
                    <div class="post-username">${post.display_name || post.username}</div>
                    <div class="post-location">${post.location || 'تهران، ایران'}</div>
                </div>
                <button class="post-menu">
                    <i class="fas fa-ellipsis-h"></i>
                </button>
            </div>
            
            <img src="${post.image_url}" alt="Post image" class="post-image" 
                 onerror="this.src='https://via.placeholder.com/600x600/cccccc/969696?text=تصویر+پست'">
            
            <div class="post-actions">
                <div class="post-actions-left">
                    <button class="action-btn like-btn ${post.is_liked ? 'liked' : ''}" data-post-id="${post.id}">
                        <i class="${post.is_liked ? 'fas' : 'far'} fa-heart"></i>
                    </button>
                    <button class="action-btn comment-btn" data-post-id="${post.id}">
                        <i class="far fa-comment"></i>
                    </button>
                    <button class="action-btn share-btn" data-post-id="${post.id}">
                        <i class="far fa-paper-plane"></i>
                    </button>
                </div>
                <button class="action-btn save-btn">
                    <i class="far fa-bookmark"></i>
                </button>
            </div>
            
            <div class="post-stats">
                <div class="post-likes">${post.likes_count.toLocaleString()} لایک</div>
                <div class="post-caption">
                    <span class="caption-username">${post.display_name || post.username}</span>
                    ${post.caption || ''}
                </div>
                <a href="#" class="view-comments" data-post-id="${post.id}">
                    مشاهده ${post.comments_count.toLocaleString()} نظر
                </a>
                <div class="post-time">${timeAgo}</div>
            </div>
            
            <div class="post-add-comment">
                <input type="text" class="comment-input" placeholder="افزودن نظر..." data-post-id="${post.id}">
                <button class="post-comment-btn" data-post-id="${post.id}" disabled>ارسال</button>
            </div>
        </div>
        `;
    });
    
    feedContainer.innerHTML = html;
    
    // Add event listeners to new posts
    setupPostEventListeners();
}

function renderStories() {
    const storiesList = document.getElementById('storiesList');
    if (!storiesList) return;
    
    if (stories.length === 0) {
        storiesList.innerHTML = `
            <div class="empty-stories">
                <p>هنوز استوری‌ای وجود ندارد</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    stories.forEach(story => {
        html += `
        <div class="story-item" data-user="${story.user.username}">
            <div class="story-avatar">
                <div class="story-avatar-inner">
                    <i class="fas fa-user"></i>
                </div>
            </div>
            <div class="story-username">${story.user.display_name}</div>
        </div>
        `;
    });
    
    storiesList.innerHTML = html;
    
    // Add click events to stories
    document.querySelectorAll('.story-item').forEach(item => {
        item.addEventListener('click', function() {
            const username = this.dataset.user;
            viewStory(username);
        });
    });
}

function renderSuggestions() {
    const suggestionsList = document.getElementById('suggestionsList');
    if (!suggestionsList) return;
    
    if (users.length === 0) {
        suggestionsList.innerHTML = '<p class="no-suggestions">هیچ کاربری برای پیشنهاد وجود ندارد</p>';
        return;
    }
    
    let html = '';
    // Show only 5 suggestions
    users.slice(0, 5).forEach(user => {
        html += `
        <div class="suggestion-item">
            <div class="suggestion-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="suggestion-info">
                <span class="suggestion-username">${user.display_name}</span>
                <span class="suggestion-followers">@${user.username}</span>
            </div>
            <button class="btn-follow" data-username="${user.username}">
                دنبال کردن
            </button>
        </div>
        `;
    });
    
    suggestionsList.innerHTML = html;
    
    // Add follow button events
    document.querySelectorAll('.btn-follow').forEach(btn => {
        btn.addEventListener('click', function() {
            const username = this.dataset.username;
            followUser(username, this);
        });
    });
}

function renderNotifications() {
    const notificationsList = document.getElementById('notificationsList');
    if (!notificationsList) return;
    
    let html = '';
    notifications.forEach(notification => {
        let icon = 'fas fa-heart';
        let text = '';
        
        switch (notification.type) {
            case 'like':
                text = `<strong>${notification.user}</strong> پست شما را لایک کرد`;
                break;
            case 'comment':
                text = `<strong>${notification.user}</strong> روی پست شما نظر داد: "${notification.text}"`;
                icon = 'fas fa-comment';
                break;
            case 'follow':
                text = `<strong>${notification.user}</strong> شما را دنبال کرد`;
                icon = 'fas fa-user-plus';
                break;
            default:
                text = notification.text;
        }
        
        html += `
        <div class="notification-item">
            <div class="notification-avatar">
                <i class="${icon}"></i>
            </div>
            <div class="notification-content">
                <div>${text}</div>
                <div class="notification-time">${notification.time}</div>
            </div>
        </div>
        `;
    });
    
    notificationsList.innerHTML = html;
}

function renderMessages() {
    const messagesList = document.getElementById('messagesList');
    if (!messagesList) return;
    
    let html = '';
    messages.forEach(msg => {
        html += `
        <div class="message-item ${msg.unread ? 'unread' : ''}" data-user="${msg.user}">
            <div class="message-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="message-info">
                <div class="message-sender">${msg.user}</div>
                <div class="message-preview">${msg.last_message}</div>
            </div>
            <div class="message-time">${msg.time}</div>
        </div>
        `;
    });
    
    messagesList.innerHTML = html;
    
    // Add click events to messages
    document.querySelectorAll('.message-item').forEach(item => {
        item.addEventListener('click', function() {
            const username = this.dataset.user;
            openChat(username);
        });
    });
}

function updateNotificationBadge() {
    const badge = document.getElementById('notificationBadge');
    if (badge) {
        const unreadCount = notifications.length; // In real app, filter unread
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'inline-block' : 'none';
    }
}

function updateMessageBadge() {
    const badge = document.getElementById('messageBadge');
    if (badge) {
        const unreadCount = messages.filter(m => m.unread).length;
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'inline-block' : 'none';
    }
}

function setupEventListeners() {
    console.log('🔧 Setting up event listeners...');
    
    // Navigation
    document.querySelectorAll('.menu-item, .nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.dataset.page;
            navigateToPage(page);
        });
    });
    
    // Create post buttons
    document.getElementById('createPostBtn')?.addEventListener('click', openCreatePostModal);
    document.getElementById('addStoryBtn')?.addEventListener('click', () => {
        document.getElementById('storyFileInput').click();
    });
    
    // File inputs
    document.getElementById('storyFileInput')?.addEventListener('change', handleStoryUpload);
    document.getElementById('postFileInput')?.addEventListener('change', handlePostFileSelect);
    document.getElementById('modalPostFileInput')?.addEventListener('change', handleModalPostFileSelect);
    
    // Post creation
    document.getElementById('submitPostBtn')?.addEventListener('click', createPost);
    
    // Modals
    document.querySelectorAll('.close-modal, .btn-cancel').forEach(btn => {
        btn.addEventListener('click', closeAllModals);
    });
    
    // Chat
    document.getElementById('sendMessageBtn')?.addEventListener('click', sendMessage);
    document.getElementById('chatMessageInput')?.addEventListener('input', handleChatTyping);
    document.getElementById('chatMessageInput')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Search
    const searchBox = document.querySelector('.search-box input');
    if (searchBox) {
        searchBox.addEventListener('input', debounce(searchUsers, 300));
    }
    
    // Infinite scroll
    window.addEventListener('scroll', handleInfiniteScroll);
    
    // Profile tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tab = this.dataset.tab;
            switchProfileTab(tab);
        });
    });
    
    console.log('✅ Event listeners setup complete');
}

function setupPostEventListeners() {
    // Like buttons
    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const postId = this.dataset.postId;
            toggleLike(postId, this);
        });
    });
    
    // Comment buttons
    document.querySelectorAll('.comment-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const postId = this.dataset.postId;
            openPostComments(postId);
        });
    });
    
    // View comments links
    document.querySelectorAll('.view-comments').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const postId = this.dataset.postId;
            openPostComments(postId);
        });
    });
    
    // Share buttons
    document.querySelectorAll('.share-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const postId = this.dataset.postId;
            sharePost(postId);
        });
    });
    
    // Comment input
    document.querySelectorAll('.comment-input').forEach(input => {
        input.addEventListener('input', function() {
            const postId = this.dataset.postId;
            const btn = document.querySelector(`.post-comment-btn[data-post-id="${postId}"]`);
            btn.disabled = !this.value.trim();
            btn.classList.toggle('active', this.value.trim());
        });
        
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && this.value.trim()) {
                e.preventDefault();
                const postId = this.dataset.postId;
                addComment(postId, this.value.trim());
                this.value = '';
                const btn = document.querySelector(`.post-comment-btn[data-post-id="${postId}"]`);
                btn.disabled = true;
                btn.classList.remove('active');
            }
        });
    });
    
    // Comment submit buttons
    document.querySelectorAll('.post-comment-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const postId = this.dataset.postId;
            const input = document.querySelector(`.comment-input[data-post-id="${postId}"]`);
            if (input && input.value.trim()) {
                addComment(postId, input.value.trim());
                input.value = '';
                this.disabled = true;
                this.classList.remove('active');
            }
        });
    });
}

async function toggleLike(postId, button) {
    try {
        const response = await fetch(`/api/posts/${postId}/like`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username: currentUser })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update button
            const icon = button.querySelector('i');
            if (data.is_liked) {
                button.classList.add('liked');
                icon.classList.remove('far');
                icon.classList.add('fas');
                
                // Add animation
                button.classList.add('liked-animation');
                setTimeout(() => button.classList.remove('liked-animation'), 300);
            } else {
                button.classList.remove('liked');
                icon.classList.remove('fas');
                icon.classList.add('far');
            }
            
            // Update likes count
            const postElement = button.closest('.post-card');
            const likesCount = postElement.querySelector('.post-likes');
            likesCount.textContent = `${data.likes_count.toLocaleString()} لایک`;
            
            // Show notification
            if (data.is_liked) {
                showNotification('پست لایک شد', 'success');
            }
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error toggling like:', error);
        showNotification('خطا در لایک کردن', 'error');
    }
}

async function addComment(postId, text) {
    try {
        const response = await fetch(`/api/posts/${postId}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: currentUser,
                text: text
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update comments count
            const postElement = document.querySelector(`.post-card[data-post-id="${postId}"]`);
            if (postElement) {
                const commentsLink = postElement.querySelector('.view-comments');
                const match = commentsLink.textContent.match(/\d+/);
                const currentCount = match ? parseInt(match[0]) : 0;
                commentsLink.textContent = `مشاهده ${(currentCount + 1).toLocaleString()} نظر`;
            }
            
            showNotification('نظر شما ثبت شد', 'success');
            
            // If comments modal is open, refresh it
            if (document.querySelector('.comments-modal')?.style.display === 'block') {
                openPostComments(postId);
            }
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error adding comment:', error);
        showNotification('خطا در ثبت نظر', 'error');
    }
}

function openPostComments(postId) {
    // In a real app, this would open a comments modal
    // For now, just log it
    console.log('Opening comments for post:', postId);
    showNotification('بخش نظرات به زودی اضافه خواهد شد', 'info');
}

function sharePost(postId) {
    const post = posts.find(p => p.id == postId);
    if (!post) return;
    
    // Create share URL
    const url = `${window.location.origin}/post/${postId}`;
    
    // Copy to clipboard
    navigator.clipboard.writeText(url).then(() => {
        showNotification('لینک پست در کلیپ‌بورد کپی شد', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('خطا در اشتراک‌گذاری', 'error');
    });
}

function openCreatePostModal() {
    const modal = document.getElementById('createPostModal');
    modal.style.display = 'flex';
    
    // Reset form
    document.getElementById('modalPostPreview').innerHTML = '';
    document.getElementById('modalPostCaption').value = '';
    document.getElementById('modalPostFileInput').value = '';
    
    // Focus on caption
    setTimeout(() => {
        document.getElementById('modalPostCaption').focus();
    }, 100);
}

function handlePostFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        openCreatePostModal();
        handleModalPostFileSelect({ target: { files: [file] } });
    }
}

function handleModalPostFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate file
    if (!file.type.startsWith('image/')) {
        showNotification('فقط فایل‌های تصویری مجاز هستند', 'error');
        return;
    }
    
    if (file.size > 10 * 1024 * 1024) { // 10MB
        showNotification('حجم فایل باید کمتر از ۱۰ مگابایت باشد', 'error');
        return;
    }
    
    // Show preview
    const reader = new FileReader();
    reader.onload = function(event) {
        const preview = document.getElementById('modalPostPreview');
        preview.innerHTML = `
            <img src="${event.target.result}" alt="Preview" 
                 style="width: 100%; border-radius: var(--radius);">
        `;
        preview.style.display = 'block';
        
        // Hide upload area
        document.getElementById('postUploadArea').style.display = 'none';
    };
    reader.readAsDataURL(file);
}

async function createPost() {
    const fileInput = document.getElementById('modalPostFileInput');
    const caption = document.getElementById('modalPostCaption').value.trim();
    const file = fileInput.files[0];
    
    if (!file) {
        showNotification('لطفاً یک عکس انتخاب کنید', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('username', currentUser);
    formData.append('caption', caption);
    formData.append('image', file);
    
    // Show loading
    const submitBtn = document.getElementById('submitPostBtn');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> در حال ارسال...';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/posts', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Close modal
            closeAllModals();
            
            // Reset form
            document.getElementById('modalPostPreview').innerHTML = '';
            document.getElementById('modalPostCaption').value = '';
            document.getElementById('modalPostFileInput').value = '';
            document.getElementById('postUploadArea').style.display = 'block';
            
            // Reload posts
            loadPosts();
            
            // Show success
            showNotification('پست با موفقیت منتشر شد', 'success');
            
            // Emit socket event
            if (socket) {
                socket.emit('new_post', {
                    username: currentUser,
                    post_id: data.post_id
                });
            }
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error creating post:', error);
        showNotification('خطا در انتشار پست', 'error');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

function handleStoryUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate file
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4'];
    if (!validTypes.includes(file.type)) {
        showNotification('فقط فایل‌های تصویری و ویدیویی مجاز هستند', 'error');
        return;
    }
    
    if (file.size > 20 * 1024 * 1024) { // 20MB
        showNotification('حجم فایل باید کمتر از ۲۰ مگابایت باشد', 'error');
        return;
    }
    
    uploadStory(file);
}

async function uploadStory(file) {
    const formData = new FormData();
    formData.append('username', currentUser);
    formData.append('media', file);
    
    try {
        const response = await fetch('/api/stories', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Reload stories
            loadStories();
            
            // Show success
            showNotification('استوری با موفقیت منتشر شد', 'success');
            
            // View the story
            viewStory(currentUser, [{
                media_url: data.media_url,
                media_type: data.media_type
            }]);
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error uploading story:', error);
        showNotification('خطا در انتشار استوری', 'error');
    } finally {
        // Reset file input
        document.getElementById('storyFileInput').value = '';
    }
}

function viewStory(username, storiesData = null) {
    // In a real app, this would open a story viewer
    // For now, just show a notification
    console.log('Viewing story for user:', username, storiesData);
    showNotification(`مشاهده استوری ${username}`, 'info');
}

function followUser(username, button) {
    console.log('Following user:', username);
    
    // Update button
    button.textContent = 'دنبال شده';
    button.style.opacity = '0.7';
    button.disabled = true;
    
    // Show notification
    showNotification(`شما ${username} را دنبال کردید`, 'success');
}

function openChat(username) {
    currentChatUser = username;
    
    // Update modal
    document.getElementById('chatUserName').textContent = username;
    document.getElementById('chatModal').style.display = 'flex';
    
    // Load messages
    loadChatMessages(username);
    
    // Join chat room
    if (socket) {
        socket.emit('join_chat', {
            username: currentUser,
            target_user: username
        });
    }
    
    // Focus on input
    setTimeout(() => {
        document.getElementById('chatMessageInput').focus();
    }, 100);
}

async function loadChatMessages(username) {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="loading-messages">
            <div class="spinner"></div>
            <p>در حال بارگذاری پیام‌ها...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`/api/chats/messages?user1=${currentUser}&user2=${username}`);
        const data = await response.json();
        
        if (data.success) {
            renderChatMessages(data.messages);
        }
    } catch (error) {
        console.error('Error loading chat messages:', error);
        chatMessages.innerHTML = '<p class="error">خطا در بارگذاری پیام‌ها</p>';
    }
}

function renderChatMessages(messages) {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = '';
    
    if (!messages || messages.length === 0) {
        chatMessages.innerHTML = `
            <div class="no-messages">
                <i class="fas fa-comments" style="font-size: 48px; color: var(--text-secondary); margin-bottom: 16px;"></i>
                <p>هنوز پیامی رد و بدل نشده است</p>
                <p style="font-size: 12px; margin-top: 8px;">اولین پیام را ارسال کنید!</p>
            </div>
        `;
        return;
    }
    
    messages.forEach(msg => {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${msg.sender === currentUser ? 'sent' : 'received'}`;
        messageElement.textContent = msg.content;
        chatMessages.appendChild(messageElement);
    });
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById('chatMessageInput');
    const message = input.value.trim();
    
    if (!message || !currentChatUser || !socket) return;
    
    // Emit socket event
    socket.emit('send_message', {
        username: currentUser,
        target_user: currentChatUser,
        message: message
    });
    
    // Add to UI
    const chatMessages = document.getElementById('chatMessages');
    
    // Remove "no messages" if present
    const noMessages = chatMessages.querySelector('.no-messages');
    if (noMessages) {
        noMessages.remove();
    }
    
    const messageElement = document.createElement('div');
    messageElement.className = 'message sent';
    messageElement.textContent = message;
    chatMessages.appendChild(messageElement);
    
    // Clear input
    input.value = '';
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Clear typing indicator
    clearTypingIndicator();
}

function handleChatTyping() {
    if (!currentChatUser || !socket) return;
    
    // Send typing event
    socket.emit('typing', {
        username: currentUser,
        target_user: currentChatUser,
        is_typing: true
    });
    
    // Clear previous timeout
    if (typingTimeout) {
        clearTimeout(typingTimeout);
    }
    
    // Set timeout to send "stopped typing"
    typingTimeout = setTimeout(() => {
        socket.emit('typing', {
            username: currentUser,
            target_user: currentChatUser,
            is_typing: false
        });
    }, 1000);
}

function clearTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    indicator.style.display = 'none';
}

function handleTypingIndicator(data) {
    if (data.username === currentChatUser) {
        const indicator = document.getElementById('typingIndicator');
        const typingUser = document.getElementById('typingUser');
        
        if (data.is_typing) {
            typingUser.textContent = data.username;
            indicator.style.display = 'block';
        } else {
            indicator.style.display = 'none';
        }
    }
}

function handleNewMessage(data) {
    // If we're in chat with this user, add the message
    if (currentChatUser === data.sender) {
        const chatMessages = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.className = 'message received';
        messageElement.textContent = data.message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Update message badge
    updateMessageBadge();
    
    // Show notification if chat is not active
    if (!currentChatUser || currentChatUser !== data.sender) {
        showNotification(`پیام جدید از ${data.sender}`, 'info');
    }
}

function handleNewNotification(data) {
    // Add to notifications
    notifications.unshift({
        id: Date.now(),
        type: data.type,
        user: data.user,
        text: data.message,
        time: 'همین الان'
    });
    
    // Update UI
    updateNotificationBadge();
    renderNotifications();
    
    // Show notification
    showNotification(data.message, 'info');
}

function handleNewPost(data) {
    // Reload posts if it's not our own post
    if (data.username !== currentUser) {
        loadPosts();
    }
}

function navigateToPage(page) {
    console.log('Navigating to page:', page);
    
    // Hide all pages
    document.querySelectorAll('.page-container').forEach(container => {
        container.style.display = 'none';
    });
    
    // Hide main content if navigating away from home
    const mainContent = document.querySelector('.main-content');
    if (page === 'home') {
        mainContent.style.display = 'grid';
    } else {
        mainContent.style.display = 'none';
    }
    
    // Show selected page
    const pageElement = document.getElementById(`${page}Page`);
    if (pageElement) {
        pageElement.style.display = 'block';
    }
    
    // Update active nav items
    document.querySelectorAll('.menu-item, .nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === page) {
            item.classList.add('active');
        }
    });
    
    // Set current page
    currentPage = page;
    
    // Load page-specific data
    switch (page) {
        case 'explore':
            loadExploreData();
            break;
        case 'messages':
            loadMessages();
            break;
        case 'notifications':
            loadNotifications();
            break;
        case 'profile':
            loadProfileData();
            break;
    }
}

function loadExploreData() {
    // This would load explore data from API
    console.log('Loading explore data...');
}

function loadProfileData() {
    // This would load profile data from API
    console.log('Loading profile data...');
}

function switchProfileTab(tab) {
    console.log('Switching to tab:', tab);
    
    // Update active tab
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tab) {
            btn.classList.add('active');
        }
    });
    
    // Load tab data
    // In a real app, this would load different content
}

function searchUsers(query) {
    // This would search users from API
    console.log('Searching for:', query);
}

function handleInfiniteScroll() {
    if (isLoading || !hasMorePosts) return;
    
    const scrollPosition = window.innerHeight + window.scrollY;
    const pageHeight = document.documentElement.scrollHeight;
    
    if (scrollPosition >= pageHeight - 500) {
        loadMorePosts();
    }
}

async function loadMorePosts() {
    if (isLoading) return;
    
    page++;
    isLoading = true;
    
    try {
        const response = await fetch(`/api/posts?page=${page}&username=${currentUser}`);
        const data = await response.json();
        
        if (data.success && data.posts.length > 0) {
            posts = [...posts, ...data.posts];
            hasMorePosts = data.has_next || false;
            renderPosts();
        } else {
            hasMorePosts = false;
        }
    } catch (error) {
        console.error('Error loading more posts:', error);
    } finally {
        isLoading = false;
    }
}

function closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
}

function showNotification(message, type = 'info') {
    // Remove existing notifications
    document.querySelectorAll('.toast').forEach(toast => toast.remove());
    
    // Create toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        </div>
        <div class="toast-message">${message}</div>
        <button class="toast-close">&times;</button>
    `;
    
    // Style
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        right: 20px;
        background-color: ${type === 'success' ? '#4CAF50' : 
                         type === 'error' ? '#f44336' : 
                         type === 'info' ? '#2196F3' : '#333'};
        color: white;
        padding: 16px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        gap: 12px;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: toastSlideIn 0.3s ease;
        font-family: 'Vazirmatn', sans-serif;
    `;
    
    // Add to page
    document.body.appendChild(toast);
    
    // Close button
    toast.querySelector('.toast-close').addEventListener('click', () => toast.remove());
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'toastSlideOut 0.3s ease';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    }, 3000);
}

function formatTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    
    if (diffSec < 60) {
        return 'همین الان';
    } else if (diffMin < 60) {
        return `${diffMin} دقیقه پیش`;
    } else if (diffHour < 24) {
        return `${diffHour} ساعت پیش`;
    } else if (diffDay === 1) {
        return 'دیروز';
    } else if (diffDay < 7) {
        return `${diffDay} روز پیش`;
    } else if (diffDay < 30) {
        return `${Math.floor(diffDay / 7)} هفته پیش`;
    } else {
        return date.toLocaleDateString('fa-IR');
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Add toast animations
const style = document.createElement('style');
style.textContent = `
    @keyframes toastSlideIn {
        from {
            transform: translateY(-100%);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    
    @keyframes toastSlideOut {
        from {
            transform: translateY(0);
            opacity: 1;
        }
        to {
            transform: translateY(-100%);
            opacity: 0;
        }
    }
    
    .liked-animation {
        animation: heartBeat 0.3s ease;
    }
`;
document.head.appendChild(style);

console.log('🎉 InstaSocial JavaScript loaded successfully!');
