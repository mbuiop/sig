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
        console.log('Connected to chat server');
    });
    
    socket.on('new_message', function(data) {
        receiveMessage(data.sender, data.message, data.timestamp);
    });
    
    socket.on('user_typing', function(data) {
        showTypingIndicator(data.username, data.is_typing);
    });
    
    socket.on('joined_chat', function(data) {
        console.log('Joined chat:', data.message);
    });
}

// Load posts from server
function loadPosts() {
    const postsContainer = document.getElementById('postsContainer');
    
    fetch('/api/posts')
        .then(response => response.json())
        .then(data => {
            if (data.posts && data.posts.length > 0) {
                renderPosts(data.posts);
            } else {
                postsContainer.innerHTML = `
                    <div class="no-posts">
                        <i class="fas fa-camera" style="font-size: 48px; color: #dbdbdb; margin-bottom: 16px;"></i>
                        <p>هنوز هیچ پستی وجود ندارد. اولین پست را ایجاد کنید!</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading posts:', error);
            postsContainer.innerHTML = `
                <div class="error-loading">
                    <p>خطا در بارگذاری پست‌ها. لطفاً دوباره تلاش کنید.</p>
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
        
        <img src="${post.image_url}" alt="Post image" class="post-image" loading="lazy">
        
        <div class="post-actions">
            <button class="post-action-btn like-btn ${post.is_liked ? 'liked' : ''}" data-post-id="${post.id}">
                <i class="fas fa-heart"></i>
            </button>
            <button class="post-action-btn comment-btn" data-post-id="${post.id}">
                <i class="fas fa-comment"></i>
            </button>
            <button class="post-action-btn share-btn">
                <i class="fas fa-paper-plane"></i>
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
    
    fetch('/api/stories')
        .then(response => response.json())
        .then(data => {
            if (data.stories && data.stories.length > 0) {
                renderStories(data.stories);
            } else {
                storiesList.innerHTML = `
                    <div class="no-stories">
                        <p>هنوز استوری‌ای وجود ندارد</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading stories:', error);
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
        storyMedia.innerHTML = `<img src="${story.media_url}" alt="Story" style="width: 100%; border-radius: 8px;">`;
    } else {
        storyMedia.innerHTML = `
            <video controls autoplay style="width: 100%; border-radius: 8px;">
                <source src="${story.media_url}" type="video/mp4">
                مرورگر شما از ویدیو پشتیبانی نمی‌کند.
            </video>
        `;
    }
    
    modal.style.display = 'flex';
    
    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Close button
    document.querySelector('#storyModal .close-modal').addEventListener('click', function() {
        modal.style.display = 'none';
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
                preview.innerHTML = `<img src="${event.target.result}" alt="Preview">`;
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
    
    // Modal close buttons
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    });
    
    // Navigation
    document.getElementById('homeBtn').addEventListener('click', function() {
        setActiveNav(this);
        // Reload posts
        loadPosts();
    });
    
    document.getElementById('chatBtn').addEventListener('click', function() {
        setActiveNav(this);
        // Show chat sidebar
        document.querySelector('.right-sidebar').style.display = 'block';
    });
    
    document.getElementById('postBtn').addEventListener('click', function() {
        setActiveNav(this);
        // Scroll to create post
        document.querySelector('.create-post-card').scrollIntoView({ behavior: 'smooth' });
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
        
        // Chat user item
        if (e.target.closest('.chat-user-item')) {
            const userItem = e.target.closest('.chat-user-item');
            const username = userItem.dataset.username;
            startChat(username);
        }
    });
}

// Create a new post
function createPost() {
    const caption = document.getElementById('postCaption').value.trim();
    const fileInput = document.getElementById('postFileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('لطفاً یک عکس انتخاب کنید');
        return;
    }
    
    const formData = new FormData();
    formData.append('username', currentUser);
    formData.append('caption', caption);
    formData.append('image', file);
    
    fetch('/api/posts', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reset form
            document.getElementById('postCaption').value = '';
            document.getElementById('postPreview').innerHTML = '';
            document.getElementById('postPreview').style.display = 'none';
            fileInput.value = '';
            
            // Reload posts
            loadPosts();
            
            // Show success message
            showNotification('پست با موفقیت منتشر شد', 'success');
        } else {
            showNotification('خطا در انتشار پست: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error creating post:', error);
        showNotification('خطا در انتشار پست', 'error');
    });
}

// Upload a story
function uploadStory(file) {
    const formData = new FormData();
    formData.append('username', currentUser);
    formData.append('media', file);
    
    fetch('/api/stories', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reload stories
            loadStories();
            
            // Show success message
            showNotification('استوری با موفقیت منتشر شد', 'success');
        } else {
            showNotification('خطا در انتشار استوری: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error uploading story:', error);
        showNotification('خطا در انتشار استوری', 'error');
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
            if (data.is_liked) {
                button.classList.add('liked');
                button.innerHTML = '<i class="fas fa-heart"></i>';
            } else {
                button.classList.remove('liked');
                button.innerHTML = '<i class="far fa-heart"></i>';
            }
            
            // Update likes count
            const postElement = button.closest('.post-card');
            const likesCountElement = postElement.querySelector('.post-likes');
            likesCountElement.textContent = `${data.likes_count} لایک`;
        }
    })
    .catch(error => {
        console.error('Error toggling like:', error);
    });
}

// Show post details with comments
function showPostDetails(postId) {
    const modal = document.getElementById('postDetailModal');
    const postDetailContent = document.getElementById('postDetailContent');
    
    // Load post and comments
    Promise.all([
        fetch(`/api/posts/${postId}/comments`).then(res => res.json()),
        // In a real app, we would also fetch post details here
    ])
    .then(([commentsData]) => {
        // For now, just show comments
        let html = `<div class="comments-section">
            <h4>نظرات</h4>`;
        
        if (commentsData.comments && commentsData.comments.length > 0) {
            commentsData.comments.forEach(comment => {
                const timeAgo = formatTimeAgo(new Date(comment.created_at));
                html += `
                <div class="comment">
                    <div class="comment-header">
                        <strong>${comment.display_name || comment.username}</strong>
                        <span class="comment-time">${timeAgo}</span>
                    </div>
                    <div class="comment-text">${comment.text}</div>
                </div>`;
            });
        } else {
            html += `<p class="no-comments">هنوز نظری وجود ندارد.</p>`;
        }
        
        // Add comment form
        html += `
            <div class="add-comment-form">
                <input type="text" id="detailCommentInput" placeholder="نظر خود را بنویسید...">
                <button id="detailCommentBtn" class="btn-primary" style="margin-top: 10px;">ارسال نظر</button>
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
        
        modal.style.display = 'flex';
        
        // Close modal when clicking outside
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    })
    .catch(error => {
        console.error('Error loading post details:', error);
        postDetailContent.innerHTML = '<p>خطا در بارگذاری اطلاعات پست</p>';
        modal.style.display = 'flex';
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
        if (data.success) {
            // Reload comments if modal is open
            if (document.getElementById('postDetailModal').style.display === 'flex') {
                showPostDetails(postId);
            }
            
            // Update comments count on post card
            const postCard = document.querySelector(`.post-card[data-post-id="${postId}"]`);
            if (postCard) {
                const commentsCountElement = postCard.querySelector('.post-comments');
                const currentCount = parseInt(commentsCountElement.textContent.match(/\d+/)[0]) || 0;
                commentsCountElement.textContent = `مشاهده ${currentCount + 1} نظر`;
            }
            
            showNotification('نظر شما ثبت شد', 'success');
        } else {
            showNotification('خطا در ثبت نظر', 'error');
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
                        // In a real app, this would navigate to user profile
                        alert(`پروفایل کاربر: ${username}`);
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
    
    // In a real app, this would fetch from server
    // For now, we'll just simulate
    if (query) {
        // Show loading
        usersList.innerHTML = '<div class="loading-chat-users">در حال جستجو...</div>';
        
        // Simulate API call
        setTimeout(() => {
            // Mock results
            const mockUsers = [
                { username: 'user2', display_name: 'کاربر دو' },
                { username: 'user3', display_name: 'کاربر سه' },
                { username: 'test', display_name: 'کاربر آزمایشی' }
            ].filter(user => 
                user.username.includes(query) || 
                user.display_name.includes(query)
            );
            
            if (mockUsers.length > 0) {
                let html = '';
                mockUsers.forEach(user => {
                    html += `
                    <div class="chat-user-item" data-username="${user.username}">
                        <div class="user-avatar-small">
                            <i class="fas fa-user"></i>
                        </div>
                        <div class="chat-user-info">
                            <div class="chat-username">${user.display_name}</div>
                            <div class="chat-last-message">@${user.username}</div>
                        </div>
                    </div>`;
                });
                usersList.innerHTML = html;
            } else {
                usersList.innerHTML = '<div class="no-users">کاربری یافت نشد</div>';
            }
        }, 300);
    } else {
        // Clear list when search is empty
        usersList.innerHTML = '';
    }
}

// Start chat with a user
function startChat(username) {
    currentChatUser = username;
    
    // Update UI
    document.getElementById('chatWithUser').textContent = username;
    document.querySelector('.chat-users').style.display = 'none';
    document.getElementById('activeChat').style.display = 'flex';
    
    // Join chat room via Socket.IO
    if (socket) {
        socket.emit('join_chat', {
            username: currentUser,
            target_user: username
        });
    }
    
    // Load previous messages (in a real app, this would fetch from server)
    loadChatMessages(username);
}

// Show chat users list
function showChatUsers() {
    document.querySelector('.chat-users').style.display = 'block';
    document.getElementById('activeChat').style.display = 'none';
    currentChatUser = null;
}

// Load chat messages
function loadChatMessages(username) {
    const messagesContainer = document.getElementById('chatMessages');
    
    // In a real app, this would fetch from server
    // For now, show empty or mock messages
    messagesContainer.innerHTML = `
        <div class="message received">
            سلام! چطوری؟
        </div>
        <div class="message sent">
            خوبم ممنون! تو چطوری؟
        </div>
    `;
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Send a message
function sendMessage() {
    const input = document.getElementById('chatMessageInput');
    const message = input.value.trim();
    
    if (!message || !currentChatUser || !socket) return;
    
    // Send via Socket.IO
    socket.emit('send_message', {
        username: currentUser,
        target_user: currentChatUser,
        message: message
    });
    
    // Add to UI immediately
    const messagesContainer = document.getElementById('chatMessages');
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
    // Only show if we're in chat with this user
    if (currentChatUser && 
        (sender === currentChatUser || 
         (sender === currentUser && currentChatUser === sender))) {
        
        const messagesContainer = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.className = sender === currentUser ? 'message sent' : 'message received';
        messageElement.textContent = message;
        messagesContainer.appendChild(messageElement);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background-color: ${type === 'success' ? '#4CAF50' : '#f44336'};
        color: white;
        padding: 16px;
        border-radius: 8px;
        z-index: 3000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideIn 0.3s ease-out;
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
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
