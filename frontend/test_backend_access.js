// Test script to check if backend is accessible
// This will help us understand if the problem is with backend availability

console.log('Testing backend accessibility...');

async function testBackendAccess() {
    const API_BASE = ''; // Using relative path for testing

    try {
        console.log('Testing health endpoint...');
        const healthResponse = await fetch(`${API_BASE}/api/health`);
        const healthData = await healthResponse.json();
        console.log('Health check:', healthData);

        if (healthResponse.ok) {
            console.log('✅ Backend is accessible');

            // Test the SSE endpoint directly
            console.log('Testing SSE endpoint...');
            const params = new URLSearchParams({
                query: 'developer',
                location: 'Paris, France',
                num_ads: '10',
                contract: 'CDI',
                remote: 'false',
                global_search: 'false',
                selected_sources: 'LinkedIn,France Travail',
                sort_option: 'Pertinence (IA)',
                ranking_engine: 'Groq / Llama 3.3',
                custom_gemini_key: '',
                lang_code: 'fr',
                lang_label: 'français',
                cv_data: ''
            });

            const streamUrl = `${API_BASE}/api/search-jobs-stream?${params.toString()}`;
            console.log('SSE URL:', streamUrl);

            // Test with a simple GET request (not SSE)
            console.log('Testing with simple GET request...');
            const testResponse = await fetch(streamUrl);

            console.log('Response status:', testResponse.status);
            console.log('Response headers:', Object.fromEntries(testResponse.headers.entries()));

            if (testResponse.ok) {
                console.log('✅ SSE endpoint is accessible');
                console.log('❌ But SSE requires EventSource, not regular fetch');
            } else {
                console.log('❌ SSE endpoint returned error status');
            }
        } else {
            console.log('❌ Backend health check failed');
            console.log('Status:', healthResponse.status);
        }
    } catch (error) {
        console.error('❌ Failed to access backend:', error);
        console.log('This could be because:');
        console.log('1. Backend server is not running');
        console.log('2. API_BASE configuration is incorrect');
        console.log('3. Network/CORS issues');
        console.log('4. Backend is running on a different port');
    }
}

// Run the test
testBackendAccess();