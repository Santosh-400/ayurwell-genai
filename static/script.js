document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const imageUpload = document.getElementById('image-upload');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');
    const removeImageBtn = document.getElementById('remove-image');

    let currentImageBase64 = null;

    // Auto-resize textarea logic could go here if we used textarea

    function appendMessage(content, isUser, source = null) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');

        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('avatar');
        avatarDiv.innerHTML = isUser ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('content');

        // Simple markdown parsing for bold and newlines
        let formattedContent = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        contentDiv.innerHTML = formattedContent;

        if (source && !isUser) {
            const sourceDiv = document.createElement('div');
            sourceDiv.style.fontSize = '0.75rem';
            sourceDiv.style.marginTop = '5px';
            sourceDiv.style.opacity = '0.7';
            sourceDiv.style.fontStyle = 'italic';
            sourceDiv.innerText = `Source: ${source}`;
            contentDiv.appendChild(sourceDiv);
        }

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    async function sendMessage() {
        const message = userInput.value.trim();

        if (!message && !currentImageBase64) return;

        // Display user message
        if (message) {
            appendMessage(message, true);
        }
        if (currentImageBase64) {
            // Optionally show the image in chat history
            const imgMsg = `<img src="${currentImageBase64}" style="max-width: 200px; border-radius: 8px;">`;
            appendMessage(imgMsg, true);
        }

        // Clear input
        userInput.value = '';
        const tempImage = currentImageBase64;
        clearImage();

        // Show loading state
        const loadingDiv = document.createElement('div');
        loadingDiv.classList.add('message', 'bot-message');
        loadingDiv.innerHTML = `
            <div class="avatar"><i class="fas fa-robot"></i></div>
            <div class="content"><i class="fas fa-spinner fa-spin"></i> Thinking...</div>
        `;
        chatHistory.appendChild(loadingDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    image: tempImage
                })
            });

            const data = await response.json();

            // Remove loading
            chatHistory.removeChild(loadingDiv);

            if (data.error) {
                appendMessage(`Error: ${data.error}`, false);
            } else {
                appendMessage(data.response, false, data.source);
            }

        } catch (error) {
            chatHistory.removeChild(loadingDiv);
            appendMessage("Sorry, something went wrong. Please try again.", false);
            console.error('Error:', error);
        }
    }

    // Event Listeners
    sendBtn.addEventListener('click', sendMessage);

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    imageUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                currentImageBase64 = e.target.result;
                imagePreview.src = currentImageBase64;
                imagePreviewContainer.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
    });

    removeImageBtn.addEventListener('click', clearImage);

    function clearImage() {
        currentImageBase64 = null;
        imageUpload.value = '';
        imagePreviewContainer.classList.add('hidden');
        imagePreview.src = '';
    }
});
