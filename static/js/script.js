/**
 * Social Media Platform - Frontend JavaScript
 * مدیریت تعاملات کاربر و ارتباط با سرور
 */

// Global variables
let currentUser = 'user1';
let socket = null;
let currentChatUser = null;
let typingTimeout = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeUser();
    loadPosts();
    loadStories();
    loadChatUsers();
    setupEventListeners();
    connectToSocket();
});

// Initialize current user
function initializeUser() {
    const usernameInput = document.getElementById('usernameInput');
    const currentUsernameSpan = document.getElementById('currentUsername');
    
    // Get saved username or use default
    const savedUsername = localStorage.getItem('social_username');
    if (savedUsername) {
        currentUser = savedUsername;
        usernameInput.value = currentUser;
        currentUsernameSpan.textContent = currentUser;
    }
    
    // Update username when changed
    usernameInput.addEventListener('change', function() {
        if (this.value.trim()) {
            currentUser = this.value.trim();
            localStorage.setItem('social_username', currentUser);
            currentUsernameSpan.textContent = currentUser;
            
            // Reload data with new username
            loadPosts();
            loadStories();
            loadChatUsers();
            
            // Reconnect socket with new username
            if (socket) {
                socket.disconnect();
                connectToSocket();
            }
        }
    });
}

// Connect to Socket.IO server
function connectToSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to chat server as:', currentUser);
        showNotification('اتصال برقرار شد', 'success');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from chat server');
        showNotification('اتصال قطع شد', 'error');
    });
    
    socket.on('new_message', function(data) {
        console.log('New message received:', data);
        receiveMessage(data.sender, data.message, data.timestamp);
    });
    
    socket.on('user_typing', function(data) {
        console.log('Typing indicator:', data);
        showTypingIndicator(data.username, data.is_typing);
    });
    
    socket.on('joined_chat', function(data) {
        console.log('Joined chat:', data.message);
    });
    
    socket.on('error', function(data) {
        console.error('Socket error:', data);
        showNotification('خطا در ارتباط: ' + data.message, 'error');
    });
}

// Load posts from server
function loadPosts() {
    const postsContainer = document.getElementById('postsContainer');
    postsContainer.innerHTML = `
        <div class="loading-posts">
            <div class="spinner"></div>
            <p>در حال بارگذاری پست‌ها...</p>
        </div>
    `;
    
    fetch('/api/posts')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Posts loaded:', data);
            if (data.posts && data.posts.length > 0) {
                renderPosts(data.posts);
            } else {
                postsContainer.innerHTML = `
                    <div class="no-posts card" style="text-align: center; padding: 40px;">
                        <i class="fas fa-camera" style="font-size: 48px; color: #dbdbdb; margin-bottom: 16px;"></i>
                        <p style="color: #8e8e8e;">هنوز هیچ پستی وجود ندارد. اولین پست را ایجاد کنید!</p>
                        <button id="createFirstPost" class="btn-primary" style="margin-top: 16px;">
                            <i class="fas fa-plus"></i>
                            ایجاد پست اول
                        </button>
                    </div>
                `;
                
                document.getElementById('createFirstPost')?.addEventListener('click', function() {
                    document.getElementById('postFileInput').click();
                });
            }
        })
        .catch(error => {
            console.error('Error loading posts:', error);
            postsContainer.innerHTML = `
                <div class="error-loading card" style="text-align: center; padding: 40px; color: #ed4956;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 16px;"></i>
                    <p>خطا در بارگذاری پست‌ها. لطفاً دوباره تلاش کنید.</p>
                    <button onclick="loadPosts()" class="btn-primary" style="margin-top: 16px;">
                        <i class="fas fa-redo"></i>
                        تلاش مجدد
                    </button>
                </div>
            `;
        });
}

// Render posts in the feed
function renderPosts(posts) {
    const postsContainer = document.getElementById('postsContainer');
    postsContainer.innerHTML = '';
    
    posts.forEach(post => {
        const postElement = createPostElement(post);
        postsContainer.appendChild(postElement);
    });
}

// Create a post element
function createPostElement(post) {
    const postElement = document.createElement('div');
    postElement.className = 'post-card card';
    postElement.dataset.postId = post.id;
    
    const timeAgo = formatTimeAgo(new Date(post.created_at));
    
    postElement.innerHTML = `
        <div class="post-header">
            <div class="post-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="post-user-info">
                <div class="post-username">${post.display_name || post.username}</div>
                <div class="post-time">${timeAgo}</div>
            </div>
        </div>
        
        <img src="${post.image_url}" alt="Post image" class="post-image" loading="lazy" 
             onerror="this.src='https://via.placeholder.com/600x600/cccccc/969696?text=تصویر+پست'">
        
        <div class="post-actions">
            <button class="post-action-btn like-btn ${post.is_liked ? 'liked' : ''}" data-post-id="${post.id}">
                <i class="${post.is_liked ? 'fas' : 'far'} fa-heart"></i>
            </button>
            <button class="post-action-btn comment-btn" data-post-id="${post.id}">
                <i class="far fa-comment"></i>
            </button>
            <button class="post-action-btn share-btn">
                <i class="far fa-paper-plane"></i>
            </button>
        </div>
        
        <div class="post-stats">
            <div class="post-likes">${post.likes_count} لایک</div>
            <div class="post-caption">
                <span class="post-caption-username">${post.display_name || post.username}</span>
                ${post.caption || ''}
            </div>
            <div class="post-comments" data-post-id="${post.id}">
                مشاهده ${post.comments_count} نظر
            </div>
        </div>
        
        <div class="post-add-comment">
            <input type="text" placeholder="افزودن نظر..." class="comment-input" data-post-id="${post.id}">
            <button class="post-comment-btn" data-post-id="${post.id}" disabled>ارسال</button>
        </div>
    `;
    
    return postElement;
}

// Load stories from server
function loadStories() {
    const storiesList = document.getElementById('storiesList');
    storiesList.innerHTML = `
        <div class="loading-stories">
            <div class="spinner" style="width: 20px; height: 20px;"></div>
        </div>
    `;
    
    fetch('/api/stories')
        .then(response => response.json())
        .then(data => {
            console.log('Stories loaded:', data);
            if (data.stories && data.stories.length > 0) {
                renderStories(data.stories);
            } else {
                storiesList.innerHTML = `
                    <div class="no-stories">
                        <p style="text-align: center; color: #8e8e8e; font-size: 12px;">هنوز استوری‌ای وجود ندارد</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading stories:', error);
            storiesList.innerHTML = `
                <div class="error-stories">
                    <p style="text-align: center; color: #ed4956; font-size: 12px;">خطا در بارگذاری استوری‌ها</p>
                </div>
            `;
        });
}

// Render stories
function renderStories(stories) {
    const storiesList = document.getElementById('storiesList');
    storiesList.innerHTML = '';
    
    stories.forEach(storyGroup => {
        const storyItem = document.createElement('div');
        storyItem.className = 'story-item';
        storyItem.dataset.username = storyGroup.user.username;
        
        const firstStory = storyGroup.stories[0];
        
        storyItem.innerHTML = `
            <div class="story-avatar">
                <div class="story-avatar-inner">
                    <i class="fas fa-user"></i>
                </div>
            </div>
            <div class="story-username">${storyGroup.user.display_name}</div>
        `;
        
        storyItem.addEventListener('click', function() {
            viewStory(storyGroup.user.username, storyGroup.stories);
        });
        
        storiesList.appendChild(storyItem);
    });
}

// View a story
function viewStory(username, stories) {
    const modal = document.getElementById('storyModal');
    const storyMedia = document.getElementById('storyMedia');
    
    // For simplicity, show first story
    const story = stories[0];
    
    if (story.media_type === 'image') {
        storyMedia.innerHTML = `
            <img src="${story.media_url}" alt="Story" 
                 style="width: 100%; max-height: 70vh; object-fit: contain; border-radius: 8px;"
                 onerror="this.src='https://via.placeholder.com/400x700/cccccc/969696?text=تصویر+استوری'">
        `;
    } else {
        storyMedia.innerHTML = `
            <video controls autoplay style="width: 100%; max-height: 70vh; border-radius: 8px;">
                <source src="${story.media_url}" type="video/mp4">
                مرورگر شما از ویدیو پشتیبانی نمی‌کند.
            </video>
        `;
    }
    
    modal.style.display = 'flex';
    
    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal || e.target.classList.contains('close-modal')) {
            modal.style.display = 'none';
        }
    });
}

// Load chat users
function loadChatUsers() {
    const chatUsersList = document.getElementById('chatUsersList');
    chatUsersList.innerHTML = `
        <div class="loading-chat-users" style="text-align: center; padding: 20px; color: #8e8e8e;">
            <div class="spinner" style="width: 20px; height: 20px; margin: 0 auto 10px;"></div>
            <p>در حال بارگذاری کاربران...</p>
        </div>
    `;
    
    fetch(`/api/chats/users?username=${encodeURIComponent(currentUser)}`)
        .then(response => response.json())
        .then(data => {
            console.log('Chat users loaded:', data);
            if (data.success && data.users && data.users.length > 0) {
                renderChatUsers(data.users);
            } else {
                chatUsersList.innerHTML = `
                    <div class="no-chat-users" style="text-align: center; padding: 40px; color: #8e8e8e;">
                        <i class="fas fa-user-friends" style="font-size: 32px; margin-bottom: 16px;"></i>
                        <p>هنوز کاربری برای چت وجود ندارد</p>
                        <p style="font-size: 12px; margin-top: 8px;">کاربران دیگر را دعوت کنید!</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading chat users:', error);
            chatUsersList.innerHTML = `
                <div class="error-chat-users" style="text-align: center; padding: 20px; color: #ed4956;">
                    <p>خطا در بارگذاری کاربران</p>
                </div>
            `;
        });
}

// Render chat users
function renderChatUsers(users) {
    const chatUsersList = document.getElementById('chatUsersList');
    chatUsersList.innerHTML = '';
    
    users.forEach(user => {
        const userElement = document.createElement('div');
        userElement.className = 'chat-user-item';
        userElement.dataset.username = user.username;
        
        userElement.innerHTML = `
            <div class="user-avatar-small">
                <i class="fas fa-user"></i>
            </div>
            <div class="chat-user-info">
                <div class="chat-username">${user.display_name}</div>
                <div class="chat-last-message">@${user.username}</div>
            </div>
        `;
        
        userElement.addEventListener('click', function() {
            startChat(user.username, user.display_name);
        });
        
        chatUsersList.appendChild(userElement);
    });
}

// Setup event listeners
function setupEventListeners() {
    // Create post
    document.getElementById('addImageBtn').addEventListener('click', function() {
        document.getElementById('postFileInput').click();
    });
    
    document.getElementById('postFileInput').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(event) {
                const preview = document.getElementById('postPreview');
                preview.innerHTML = `<img src="${event.target.result}" alt="Preview" style="width: 100%; border-radius: 8px;">`;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });
    
    document.getElementById('submitPostBtn').addEventListener('click', createPost);
    
    // Create story
    document.getElementById('createStoryBtn').addEventListener('click', function() {
        document.getElementById('storyFileInput').click();
    });
    
    document.getElementById('storyFileInput').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            uploadStory(file);
        }
    });
    
    // Search users
    document.getElementById('searchInput').addEventListener('input', debounce(searchUsers, 300));
    
    // Chat
    document.getElementById('chatSearchInput').addEventListener('input', debounce(searchChatUsers, 300));
    document.getElementById('sendMessageBtn').addEventListener('click', sendMessage);
    document.getElementById('chatMessageInput').addEventListener('input', handleTyping);
    document.getElementById('backToUsersBtn').addEventListener('click', showChatUsers);
    
    // Enter key for chat
    document.getElementById('chatMessageInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Modal close buttons
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    });
    
    // Navigation
    document.getElementById('homeBtn').addEventListener('click', function() {
        setActiveNav(this);
        loadPosts();
    });
    
    document.getElementById('chatBtn').addEventListener('click', function() {
        setActiveNav(this);
        loadChatUsers();
    });
    
    document.getElementById('postBtn').addEventListener('click', function() {
        setActiveNav(this);
        document.querySelector('.create-post-card').scrollIntoView({ behavior: 'smooth' });
    });
    
    document.getElementById('storyBtn').addEventListener('click', function() {
        setActiveNav(this);
        document.getElementById('storyFileInput').click();
    });
    
    // Event delegation for dynamic elements
    document.addEventListener('click', function(e) {
        // Like button
        if (e.target.closest('.like-btn')) {
            const btn = e.target.closest('.like-btn');
            const postId = btn.dataset.postId;
            toggleLike(postId, btn);
        }
        
        // Comment button
        if (e.target.closest('.comment-btn')) {
            const btn = e.target.closest('.comment-btn');
            const postId = btn.dataset.postId;
            showPostDetails(postId);
        }
        
        // View comments
        if (e.target.closest('.post-comments')) {
            const element = e.target.closest('.post-comments');
            const postId = element.dataset.postId;
            showPostDetails(postId);
        }
        
        // Enable comment button when typing
        if (e.target.classList.contains('comment-input')) {
            const postId = e.target.dataset.postId;
            const commentBtn = document.querySelector(`.post-comment-btn[data-post-id="${postId}"]`);
            
            e.target.addEventListener('input', function() {
                commentBtn.disabled = !this.value.trim();
            });
            
            // Submit comment on Enter
            e.target.addEventListener('keypress', function(event) {
                if (event.key === 'Enter' && this.value.trim()) {
                    event.preventDefault();
                    addComment(postId, this.value.trim());
                    this.value = '';
                    commentBtn.disabled = true;
                }
            });
        }
        
        // Submit comment button
        if (e.target.classList.contains('post-comment-btn') && !e.target.disabled) {
            const postId = e.target.dataset.postId;
            const input = document.querySelector(`.comment-input[data-post-id="${postId}"]`);
            if (input && input.value.trim()) {
                addComment(postId, input.value.trim());
                input.value = '';
                e.target.disabled = true;
            }
        }
    });
}

// Create a new post
function createPost() {
    const caption = document.getElementById('postCaption').value.trim();
    const fileInput = document.getElementById('postFileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        showNotification('لطفاً یک عکس انتخاب کنید', 'error');
        return;
    }
    
    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
        showNotification('حجم فایل باید کمتر از ۵ مگابایت باشد', 'error');
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
    
    fetch('/api/posts', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Post creation response:', data);
        
        if (data.success) {
            // Reset form
            document.getElementById('postCaption').value = '';
            document.getElementById('postPreview').innerHTML = '';
            document.getElementById('postPreview').style.display = 'none';
            fileInput.value = '';
            
            // Reload posts
            loadPosts();
            
            // Show success message
            showNotification(data.message || 'پست با موفقیت منتشر شد', 'success');
        } else {
            showNotification(data.error || 'خطا در انتشار پست', 'error');
        }
    })
    .catch(error => {
        console.error('Error creating post:', error);
        showNotification('خطا در ارتباط با سرور', 'error');
    })
    .finally(() => {
        // Restore button
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

// Upload a story
function uploadStory(file) {
    // Validate file size (max 10MB for videos, 5MB for images)
    const maxSize = file.type.startsWith('video/') ? 10 * 1024 * 1024 : 5 * 1024 * 1024;
    if (file.size > maxSize) {
        showNotification(`حجم فایل باید کمتر از ${maxSize / (1024 * 1024)} مگابایت باشد`, 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('username', currentUser);
    formData.append('media', file);
    
    // Show loading
    const storyBtn = document.getElementById('createStoryBtn');
    const originalText = storyBtn.innerHTML;
    storyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> در حال ارسال...';
    storyBtn.disabled = true;
    
    fetch('/api/stories', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Story creation response:', data);
        
        if (data.success) {
            // Reload stories
            loadStories();
            
            // Show success message
            showNotification(data.message || 'استوری با موفقیت منتشر شد', 'success');
            
            // Auto view the story
            setTimeout(() => {
                viewStory(currentUser, [{
                    media_url: data.media_url,
                    media_type: data.media_type
                }]);
            }, 500);
        } else {
            showNotification(data.error || 'خطا در انتشار استوری', 'error');
        }
    })
    .catch(error => {
        console.error('Error uploading story:', error);
        showNotification('خطا در ارتباط با سرور', 'error');
    })
    .finally(() => {
        // Restore button
        storyBtn.innerHTML = originalText;
        storyBtn.disabled = false;
        document.getElementById('storyFileInput').value = '';
    });
}

// Toggle like on a post
function toggleLike(postId, button) {
    fetch(`/api/posts/${postId}/like`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username: currentUser })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update button appearance
            const icon = button.querySelector('i');
            if (data.is_liked) {
                button.classList.add('liked');
                icon.classList.remove('far');
                icon.classList.add('fas');
            } else {
                button.classList.remove('liked');
                icon.classList.remove('fas');
                icon.classList.add('far');
            }
            
            // Update likes count
            const postElement = button.closest('.post-card');
            const likesCountElement = postElement.querySelector('.post-likes');
            likesCountElement.textContent = `${data.likes_count} لایک`;
        }
    })
    .catch(error => {
        console.error('Error toggling like:', error);
        showNotification('خطا در ثبت لایک', 'error');
    });
}

// Show post details with comments
function showPostDetails(postId) {
    const modal = document.getElementById('postDetailModal');
    const postDetailContent = document.getElementById('postDetailContent');
    
    postDetailContent.innerHTML = `
        <div class="loading-post-detail" style="text-align: center; padding: 40px;">
            <div class="spinner"></div>
            <p>در حال بارگذاری نظرات...</p>
        </div>
    `;
    
    modal.style.display = 'flex';
    
    // Load comments
    fetch(`/api/posts/${postId}/comments`)
        .then(response => response.json())
        .then(commentsData => {
            console.log('Comments loaded:', commentsData);
            
            let html = `<div class="comments-section">
                <h4>نظرات</h4>`;
            
            if (commentsData.comments && commentsData.comments.length > 0) {
                commentsData.comments.forEach(comment => {
                    const timeAgo = formatTimeAgo(new Date(comment.created_at));
                    html += `
                    <div class="comment" style="padding: 12px 0; border-bottom: 1px solid #f0f0f0;">
                        <div class="comment-header" style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <strong>${comment.display_name || comment.username}</strong>
                            <span class="comment-time" style="color: #8e8e8e; font-size: 12px;">${timeAgo}</span>
                        </div>
                        <div class="comment-text">${comment.text}</div>
                    </div>`;
                });
            } else {
                html += `<p class="no-comments" style="text-align: center; color: #8e8e8e; padding: 20px;">هنوز نظری وجود ندارد.</p>`;
            }
            
            // Add comment form
            html += `
                <div class="add-comment-form" style="margin-top: 20px;">
                    <div style="display: flex; gap: 10px;">
                        <input type="text" id="detailCommentInput" placeholder="نظر خود را بنویسید..." 
                               style="flex: 1; padding: 10px; border: 1px solid #dbdbdb; border-radius: 8px;">
                        <button id="detailCommentBtn" class="btn-primary">ارسال</button>
                    </div>
                </div>
            `;
            
            postDetailContent.innerHTML = html;
            
            // Add event listener for comment submission
            document.getElementById('detailCommentBtn').addEventListener('click', function() {
                const input = document.getElementById('detailCommentInput');
                if (input.value.trim()) {
                    addComment(postId, input.value.trim());
                    input.value = '';
                }
            });
            
            // Enter key for comment
            document.getElementById('detailCommentInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && this.value.trim()) {
                    e.preventDefault();
                    document.getElementById('detailCommentBtn').click();
                }
            });
        })
        .catch(error => {
            console.error('Error loading post details:', error);
            postDetailContent.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #ed4956;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 16px;"></i>
                    <p>خطا در بارگذاری نظرات</p>
                </div>
            `;
        });
    
    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Add a comment to a post
function addComment(postId, text) {
    fetch(`/api/posts/${postId}/comments`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: currentUser,
            text: text
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Comment response:', data);
        if (data.success) {
            // Reload comments if modal is open
            if (document.getElementById('postDetailModal').style.display === 'flex') {
                showPostDetails(postId);
            }
            
            // Update comments count on post card
            const postCard = document.querySelector(`.post-card[data-post-id="${postId}"]`);
            if (postCard) {
                const commentsCountElement = postCard.querySelector('.post-comments');
                const match = commentsCountElement.textContent.match(/\d+/);
                const currentCount = match ? parseInt(match[0]) : 0;
                commentsCountElement.textContent = `مشاهده ${currentCount + 1} نظر`;
            }
            
            showNotification('نظر شما ثبت شد', 'success');
        } else {
            showNotification(data.error || 'خطا در ثبت نظر', 'error');
        }
    })
    .catch(error => {
        console.error('Error adding comment:', error);
        showNotification('خطا در ثبت نظر', 'error');
    });
}

// Search for users
function searchUsers() {
    const query = document.getElementById('searchInput').value.trim();
    const resultsContainer = document.getElementById('searchResults');
    
    if (query.length < 2) {
        resultsContainer.style.display = 'none';
        return;
    }
    
    fetch(`/api/users/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (data.users && data.users.length > 0) {
                let html = '';
                data.users.forEach(user => {
                    html += `
                    <div class="search-result-item" data-username="${user.username}">
                        <i class="fas fa-user"></i>
                        <div>
                            <div>${user.display_name}</div>
                            <small>@${user.username}</small>
                        </div>
                    </div>`;
                });
                resultsContainer.innerHTML = html;
                resultsContainer.style.display = 'block';
                
                // Add click event to search results
                document.querySelectorAll('.search-result-item').forEach(item => {
                    item.addEventListener('click', function() {
                        const username = this.dataset.username;
                        startChat(username, username);
                        resultsContainer.style.display = 'none';
                        document.getElementById('searchInput').value = '';
                    });
                });
            } else {
                resultsContainer.innerHTML = '<div class="search-result-item">کاربری یافت نشد</div>';
                resultsContainer.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error searching users:', error);
        });
}

// Search for chat users
function searchChatUsers() {
    const query = document.getElementById('chatSearchInput').value.trim();
    const usersList = document.getElementById('chatUsersList');
    
    if (!query) {
        loadChatUsers();
        return;
    }
    
    usersList.innerHTML = '<div class="loading-chat-users">در حال جستجو...</div>';
    
    // This would normally be an API call
    // For now, we'll filter existing users
    setTimeout(() => {
        const userItems = document.querySelectorAll('.chat-user-item');
        let found = false;
        
        userItems.forEach(item => {
            const username = item.dataset.username;
            const displayName = item.querySelector('.chat-username').textContent;
            
            if (username.includes(query) || displayName.includes(query)) {
                item.style.display = 'flex';
                found = true;
            } else {
                item.style.display = 'none';
            }
        });
        
        if (!found) {
            usersList.innerHTML = '<div class="no-users">کاربری یافت نشد</div>';
        }
    }, 300);
}

// Start chat with a user
function startChat(username, displayName) {
    currentChatUser = username;
    
    // Update UI
    document.getElementById('chatWithUser').textContent = displayName || username;
    document.querySelector('.chat-users').style.display = 'none';
    document.getElementById('activeChat').style.display = 'flex';
    
    // Join chat room via Socket.IO
    if (socket) {
        socket.emit('join_chat', {
            username: currentUser,
            target_user: username
        });
    }
    
    // Load previous messages
    loadChatMessages(username);
    
    // Focus on message input
    setTimeout(() => {
        document.getElementById('chatMessageInput').focus();
    }, 100);
}

// Show chat users list
function showChatUsers() {
    document.querySelector('.chat-users').style.display = 'block';
    document.getElementById('activeChat').style.display = 'none';
    currentChatUser = null;
    
    // Clear typing indicator
    clearTypingIndicator();
}

// Load chat messages
function loadChatMessages(username) {
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.innerHTML = `
        <div class="loading-messages" style="text-align: center; padding: 40px; color: #8e8e8e;">
            <div class="spinner" style="width: 20px; height: 20px; margin: 0 auto 10px;"></div>
            <p>در حال بارگذاری پیام‌ها...</p>
        </div>
    `;
    
    fetch(`/api/chats/messages?user1=${encodeURIComponent(currentUser)}&user2=${encodeURIComponent(username)}`)
        .then(response => response.json())
        .then(data => {
            console.log('Chat messages loaded:', data);
            
            if (data.success && data.messages && data.messages.length > 0) {
                messagesContainer.innerHTML = '';
                data.messages.forEach(msg => {
                    const messageElement = document.createElement('div');
                    messageElement.className = `message ${msg.sender === currentUser ? 'sent' : 'received'}`;
                    messageElement.textContent = msg.content;
                    messagesContainer.appendChild(messageElement);
                });
            } else {
                messagesContainer.innerHTML = `
                    <div class="no-messages" style="text-align: center; padding: 40px; color: #8e8e8e;">
                        <i class="fas fa-comments" style="font-size: 32px; margin-bottom: 16px;"></i>
                        <p>هنوز پیامی رد و بدل نشده است</p>
                        <p style="font-size: 12px; margin-top: 8px;">اولین پیام را شما ارسال کنید!</p>
                    </div>
                `;
            }
            
            // Scroll to bottom
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        })
        .catch(error => {
            console.error('Error loading chat messages:', error);
            messagesContainer.innerHTML = `
                <div class="error-messages" style="text-align: center; padding: 40px; color: #ed4956;">
                    <p>خطا در بارگذاری پیام‌ها</p>
                </div>
            `;
        });
}

// Send a message
function sendMessage() {
    const input = document.getElementById('chatMessageInput');
    const message = input.value.trim();
    
    if (!message || !currentChatUser || !socket) {
        if (!message) {
            showNotification('پیام را وارد کنید', 'error');
        }
        return;
    }
    
    // Send via Socket.IO
    socket.emit('send_message', {
        username: currentUser,
        target_user: currentChatUser,
        message: message
    });
    
    // Also save to database via REST API
    fetch('/api/chats/messages', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            sender: currentUser,
            receiver: currentChatUser,
            content: message
        })
    }).catch(error => {
        console.error('Error saving message:', error);
    });
    
    // Add to UI immediately
    const messagesContainer = document.getElementById('chatMessages');
    
    // Remove "no messages" message if present
    const noMessages = messagesContainer.querySelector('.no-messages');
    if (noMessages) {
        noMessages.remove();
    }
    
    const messageElement = document.createElement('div');
    messageElement.className = 'message sent';
    messageElement.textContent = message;
    messagesContainer.appendChild(messageElement);
    
    // Clear input
    input.value = '';
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Clear typing indicator
    clearTypingIndicator();
}

// Receive a message
function receiveMessage(sender, message, timestamp) {
    console.log('Received message from:', sender, 'to:', currentUser, 'currentChatUser:', currentChatUser);
    
    // Only show if we're in chat with this user or if it's from current chat user
    if (currentChatUser === sender || (!currentChatUser && sender)) {
        const messagesContainer = document.getElementById('chatMessages');
        
        // Remove "no messages" message if present
        const noMessages = messagesContainer.querySelector('.no-messages');
        if (noMessages) {
            noMessages.remove();
        }
        
        // Remove loading message if present
        const loadingMessages = messagesContainer.querySelector('.loading-messages');
        if (loadingMessages) {
            loadingMessages.remove();
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = sender === currentUser ? 'message sent' : 'message received';
        messageElement.textContent = message;
        messagesContainer.appendChild(messageElement);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Show notification if chat is not active
        if (!currentChatUser || document.getElementById('activeChat').style.display === 'none') {
            showNotification(`پیام جدید از ${sender}`, 'info');
        }
    }
}

// Handle typing indicator
function handleTyping() {
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
    
    // Set timeout to send "stopped typing" after 1 second of inactivity
    typingTimeout = setTimeout(() => {
        if (socket) {
            socket.emit('typing', {
                username: currentUser,
                target_user: currentChatUser,
                is_typing: false
            });
        }
    }, 1000);
}

// Show typing indicator
function showTypingIndicator(username, isTyping) {
    const indicator = document.getElementById('typingIndicator');
    
    if (username === currentChatUser) {
        if (isTyping) {
            indicator.style.display = 'block';
            indicator.innerHTML = `<span>${username} در حال تایپ است...</span>`;
        } else {
            indicator.style.display = 'none';
        }
    }
}

// Clear typing indicator
function clearTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    indicator.style.display = 'none';
}

// Utility function: Debounce
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

// Utility function: Format time ago
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
    } else {
        return date.toLocaleDateString('fa-IR');
    }
}

// Utility function: Show notification
function showNotification(message, type) {
    // Remove existing notifications
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Style based on type
    const bgColor = type === 'success' ? '#4CAF50' : 
                   type === 'error' ? '#f44336' : 
                   type === 'info' ? '#2196F3' : '#333';
    
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        left: 20px;
        right: 20px;
        background-color: ${bgColor};
        color: white;
        padding: 16px;
        border-radius: 8px;
        z-index: 3000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideIn 0.3s ease-out;
        text-align: center;
        font-family: 'Vazirmatn', sans-serif;
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Utility function: Set active navigation button
function setActiveNav(button) {
    document.querySelectorAll('.nav-icon').forEach(btn => {
        btn.classList.remove('active');
    });
    button.classList.add('active');
}

// Add CSS animations for notifications
if (!document.querySelector('#notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateY(-20px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateY(0);
                opacity: 1;
            }
            to {
                transform: translateY(-20px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
                  }
