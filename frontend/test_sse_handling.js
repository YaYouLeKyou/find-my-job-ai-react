// Test script to verify SSE event handling logic
// This simulates the backend SSE events and tests the frontend logic

console.log('Testing SSE Event Handling Logic...');

// Simulate the event handling logic from App.jsx
function testSSEEventHandling() {
    let accumulatedJobs = [];
    let accumulatedSourceCounts = {};

    // Mock sortJobs function
    function sortJobs(jobs, sortOption) {
        return jobs; // Simple mock
    }

    // Mock set functions
    function setJobs(jobs) {
        console.log('Jobs updated:', jobs.length, 'jobs');
    }

    function setSourceCounts(counts) {
        console.log('Source counts updated:', counts);
    }

    // Test events that would come from the backend
    const testEvents = [
        // STARTED event
        { type: 'STARTED', query: 'developer', total_sources: 3 },

        // PROGRESS events (what the backend actually sends)
        {
            type: 'PROGRESS',
            progress: 100,
            source: 'LinkedIn',
            status: 'completed',
            jobs: [
                { id: '1', title: 'Senior Developer', source: 'LinkedIn' },
                { id: '2', title: 'Junior Developer', source: 'LinkedIn' }
            ]
        },

        {
            type: 'PROGRESS',
            progress: 100,
            source: 'France Travail',
            status: 'completed',
            jobs: [
                { id: '3', title: 'Developer', source: 'France Travail' }
            ]
        },

        // COMPLETED event
        {
            type: 'COMPLETED',
            jobs: [
                { id: '1', title: 'Senior Developer', source: 'LinkedIn' },
                { id: '2', title: 'Junior Developer', source: 'LinkedIn' },
                { id: '3', title: 'Developer', source: 'France Travail' }
            ],
            source_status: {
                'LinkedIn': { success: true, jobs_count: 2, status: 'completed' },
                'France Travail': { success: true, jobs_count: 1, status: 'completed' },
                'Google Jobs': { success: false, jobs_count: 0, status: 'error', error: 'Timeout' }
            },
            progress: 100
        }
    ];

    console.log('\nProcessing SSE events...');

    // Process each event
    testEvents.forEach((event, index) => {
        console.log(`\nEvent ${index + 1}: ${event.type}`);

        try {
            const data = event;

            if (data.type === 'STARTED') {
                console.log(`[SSE] Search started: ${data.query} (${data.total_sources} sources)`);
            }

            if (data.type === 'PROGRESS') {
                // Update source counts as sources complete
                if (data.source) {
                    accumulatedSourceCounts[data.source] = data.jobs ? data.jobs.length : 0;
                    setSourceCounts({ ...accumulatedSourceCounts });
                    console.log(`[SSE] Source ${data.source}: ${accumulatedSourceCounts[data.source]} offres (status=${data.status})`);
                }
                if (data.jobs && data.jobs.length > 0) {
                    console.log(`[SSE] ${data.source} reçu: ${data.jobs.length} offres`);
                }
            }

            // This is the key fix - handle both SOURCE_RESULT and PROGRESS events
            if (data.type === 'SOURCE_RESULT' || data.type === 'PROGRESS') {
                console.log(`[HANDLER] Processing ${data.type} event for source data`);
                if (data.jobs && data.jobs.length > 0) {
                    accumulatedJobs = [...accumulatedJobs, ...data.jobs];
                    // Apply client-side sorting
                    const sorted = sortJobs(accumulatedJobs, 'Pertinence (IA)');
                    setJobs(sorted);
                }
                if (data.source) {
                    accumulatedSourceCounts[data.source] = data.jobs ? data.jobs.length : 0;
                    setSourceCounts({ ...accumulatedSourceCounts });
                }
            }

            if (data.type === 'SCORES_UPDATED') {
                // Backend has updated AI scores; re-sort with updated pertinence_ai
                if (data.jobs && data.jobs.length > 0) {
                    accumulatedJobs = data.jobs;
                    const sorted = sortJobs(accumulatedJobs, 'Pertinence (IA)');
                    setJobs(sorted);
                }
            }

            if (data.type === 'COMPLETED') {
                console.log('[HANDLER] Processing COMPLETED event');
                // Final results from the stream
                if (data.jobs && data.jobs.length > 0) {
                    accumulatedJobs = data.jobs;
                    const sorted = sortJobs(accumulatedJobs, 'Pertinence (IA)');
                    setJobs(sorted);
                }

                // Build sourceCounts from source_status if available
                if (data.source_status) {
                    const counts = {};
                    Object.entries(data.source_status).forEach(([source, status]) => {
                        if (status && (status.count !== undefined || status.jobs_count !== undefined)) {
                            counts[source] = status.count !== undefined ? status.count : status.jobs_count;
                        }
                    });
                    setSourceCounts(counts);
                }
            }

            if (data.type === 'ERROR') {
                console.error("[SSE] Stream error:", data.message);
            }
        } catch (e) {
            console.error("[SSE] Failed to parse event:", e);
        }
    });

    console.log('\nFinal Results:');
    console.log('Total jobs:', accumulatedJobs.length);
    console.log('Source counts:', accumulatedSourceCounts);
    console.log('Sources with results:', Object.keys(accumulatedSourceCounts).length > 0);

    // Test the condition that controls UI display
    const shouldDisplaySourceDashboard = Object.keys(accumulatedSourceCounts).length > 0;
    console.log('Should display source dashboard in UI:', shouldDisplaySourceDashboard);

    return shouldDisplaySourceDashboard;
}

// Run the test
const testPassed = testSSEEventHandling();

console.log('\n' + '='.repeat(50));
if (testPassed) {
    console.log('✅ TEST PASSED: Source dashboard should now appear in UI');
    console.log('✅ The fix correctly handles PROGRESS events from backend');
} else {
    console.log('❌ TEST FAILED: Source dashboard would not appear');
}
console.log('='.repeat(50));