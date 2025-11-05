// Cloudflare Worker for TeleStore File Upload
// Deploy this to your Cloudflare Workers account

// Configuration - only set BACKEND_URL, credentials will be fetched automatically
const CONFIG = {
  BACKEND_URL: 'https://upload-pipeline-fix.preview.emergentagent.com', // Your TeleStore backend
  MAX_FILE_SIZE: 2000 * 1024 * 1024, // 2GB limit for Telegram
  CACHE_DURATION: 3600000, // 1 hour in milliseconds
};

// In-memory cache for credentials
let credentialsCache = {
  data: null,
  timestamp: 0,
  userId: null
};

// Function to fetch credentials from backend
async function getCredentials(userId, authToken) {
  const now = Date.now();
  
  // Return cached credentials if still valid and for same user
  if (credentialsCache.data && 
      credentialsCache.userId === userId && 
      (now - credentialsCache.timestamp) < CONFIG.CACHE_DURATION) {
    return credentialsCache.data;
  }
  
  // Fetch fresh credentials from backend
  try {
    const response = await fetch(`${CONFIG.BACKEND_URL}/api/worker/credentials`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch credentials: ${response.statusText}`);
    }
    
    const credentials = await response.json();
    
    // Cache the credentials
    credentialsCache = {
      data: credentials,
      timestamp: now,
      userId: userId
    };
    
    return credentials;
  } catch (error) {
    // If cache exists, use it even if expired (fallback)
    if (credentialsCache.data && credentialsCache.userId === userId) {
      console.warn('Using expired cache due to fetch error:', error);
      return credentialsCache.data;
    }
    throw error;
  }
}

export default {
  async fetch(request, env) {
    // Handle CORS
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        },
      });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const formData = await request.formData();
      const file = formData.get('file');
      const userId = formData.get('userId');
      const authToken = formData.get('authToken'); // User's auth token for fetching credentials
      const fileName = formData.get('fileName') || file.name;

      if (!file) {
        return new Response(JSON.stringify({ error: 'No file provided' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      if (!authToken) {
        return new Response(JSON.stringify({ error: 'Auth token required' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      // Check file size
      if (file.size > CONFIG.MAX_FILE_SIZE) {
        return new Response(JSON.stringify({ error: 'File too large (max 2GB)' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      // Fetch credentials from backend (or use cache)
      const credentials = await getCredentials(userId, authToken);

      // Convert file to buffer
      const arrayBuffer = await file.arrayBuffer();
      const buffer = new Uint8Array(arrayBuffer);

      // Upload to Telegram using bot API
      const telegramFormData = new FormData();
      telegramFormData.append('chat_id', credentials.channel_id);
      telegramFormData.append('document', new Blob([buffer]), fileName);
      telegramFormData.append('caption', `Uploaded: ${fileName}`);

      const telegramResponse = await fetch(
        `https://api.telegram.org/bot${credentials.bot_token}/sendDocument`,
        {
          method: 'POST',
          body: telegramFormData,
        }
      );

      const telegramResult = await telegramResponse.json();

      if (!telegramResult.ok) {
        throw new Error(telegramResult.description || 'Telegram upload failed');
      }

      const messageId = telegramResult.result.message_id;
      
      // Telegram returns different properties based on file type
      // Videos: result.video, Documents: result.document, Audio: result.audio, Photos: result.photo
      const fileId = telegramResult.result.document?.file_id 
        || telegramResult.result.video?.file_id
        || telegramResult.result.audio?.file_id
        || telegramResult.result.photo?.[0]?.file_id
        || null;
      
      if (!fileId) {
        throw new Error('Failed to get file_id from Telegram response');
      }

      // Note: File metadata is created by the frontend after upload
      // No need to notify backend here to avoid blocking the response

      return new Response(
        JSON.stringify({
          success: true,
          messageId,
          fileId,
          fileName,
        }),
        {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      );
    } catch (error) {
      return new Response(
        JSON.stringify({ error: error.message }),
        {
          status: 500,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      );
    }
  },
};
