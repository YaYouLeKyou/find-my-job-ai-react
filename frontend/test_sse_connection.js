// Simple test to check SSE connection
// This will help us understand if the problem is with the connection or the event handling

console.log('Testing SSE Connection...');

// Test the SSE connection with a simple query
async function testSSEConnection() {
    const API_BASE = ''; // Will use relative path for testing
    const query = 'developer';
    const location = 'Paris, France';

    const params = new URLSearchParams({
        query: query,
        location: location,
        num_ads: '10',
        contract: 'CDI',
        remote: 'false',
        global_search: 'false',
        selected_sources: 'LinkedIn,France Travail,Google Jobs',
        sort_option: 'Pertinence (IA)',
        ranking_engine: 'Groq / Llama 3.3',
        custom_gemini_key: '',
        lang_code: 'fr',
        lang_label: 'français',
        cv_data: ''
    });

    const streamUrl = `/api/search-jobs-stream?${params.toString()}`;
    console.log('Connecting to:', streamUrl);

    try {
        const eventSource = new EventSource(streamUrl);

        eventSource.onopen = () => {
            console.log('✅ SSE Connection opened successfully');
        };

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('📦 Event received:', data.type);

                if (data.type === 'STARTED') {
                    console.log('🚀 Search started:', data.query, 'with', data.total_sources, 'sources');
                }

                if (data.type === 'PROGRESS') {
                    console.log('📊 Progress from', data.source, ':', data.jobs ? data.jobs.length : 0, 'jobs');
                }

                if (data.type === 'COMPLETED') {
                    console.log('✅ Search completed with', data.jobs ? data.jobs.length : 0, 'total jobs');
                    console.log('📋 Source status:', data.source_status);
                    eventSource.close();
                }

                if (data.type === 'ERROR') {
                    console.log('❌ Error:', data.message);
                    eventSource.close();
                }
            } catch (e) {
                console.error('❌ Error parsing event:', e);
                console.log('Raw event data:', event.data);
            }
        };

        eventSource.onerror = (error) => {
            console.error('❌ SSE Connection error:', error);
            eventSource.close();
        };

        // Close connection after 30 seconds for testing
        setTimeout(() => {
            console.log('⏰ Test timeout reached, closing connection');
            eventSource.close();
        }, 30000);

    } catch (error) {
        console.error('❌ Failed to create EventSource:', error);
    }
}

// Run the test
testSSEConnection();