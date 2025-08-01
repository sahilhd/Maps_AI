// MapsAI - NVIDIA Powered Navigation Chatbot JavaScript

class NaviChatbot {
    constructor() {
        this.map = null;
        this.markers = [];
        this.directionsService = null;
        this.directionsRenderer = null;
        this.currentRoute = null;
        
        this.initializeElements();
        this.initializeMap();
        this.setupEventListeners();
    }

    initializeElements() {
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.status = document.getElementById('status');
        this.mapInfo = document.getElementById('mapInfo');
        this.sendIcon = document.getElementById('sendIcon');
        this.sendText = document.getElementById('sendText');
    }

    initializeMap() {
        // Initialize Google Maps
        const mapOptions = {
            center: { lat: 37.7749, lng: -122.4194 }, // San Francisco
            zoom: 10,
            styles: [
                {
                    "featureType": "all",
                    "elementType": "geometry",
                    "stylers": [{"color": "#242f3e"}]
                },
                {
                    "featureType": "all",
                    "elementType": "labels.text.stroke",
                    "stylers": [{"lightness": -80}]
                },
                {
                    "featureType": "administrative",
                    "elementType": "labels.text.fill",
                    "stylers": [{"color": "#746855"}]
                },
                {
                    "featureType": "poi",
                    "elementType": "labels.text.fill",
                    "stylers": [{"color": "#d59563"}]
                },
                {
                    "featureType": "road.highway",
                    "elementType": "geometry.stroke",
                    "stylers": [{"color": "#76b900"}, {"lightness": -40}]
                },
                {
                    "featureType": "road.arterial",
                    "elementType": "geometry.stroke",
                    "stylers": [{"color": "#76b900"}, {"lightness": -20}]
                },
                {
                    "featureType": "water",
                    "elementType": "geometry",
                    "stylers": [{"color": "#17263c"}]
                }
            ]
        };

        this.map = new google.maps.Map(document.getElementById('map'), mapOptions);
        this.directionsService = new google.maps.DirectionsService();
        this.directionsRenderer = new google.maps.DirectionsRenderer({
            polylineOptions: {
                strokeColor: '#76b900',
                strokeWeight: 4,
                strokeOpacity: 0.8
            },
            markerOptions: {
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    scale: 8,
                    fillColor: '#76b900',
                    fillOpacity: 1,
                    strokeColor: '#ffffff',
                    strokeWeight: 2
                }
            }
        });
        this.directionsRenderer.setMap(this.map);
    }

    setupEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enter key press
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize chat input
        this.chatInput.addEventListener('input', () => {
            this.chatInput.style.height = 'auto';
            this.chatInput.style.height = this.chatInput.scrollHeight + 'px';
        });
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;

        // Disable input while processing
        this.setLoading(true);
        
        // Add user message to chat
        this.addMessage(message, 'user');
        this.chatInput.value = '';

        try {
            // Call the backend API
            const response = await this.callNavigationAPI(message);
            
            // Process and display the response
            await this.handleAPIResponse(response, message);
            
        } catch (error) {
            console.error('API Error:', error);
            this.addMessage('❌ Sorry, I encountered an error processing your request. Please try again.', 'bot');
            this.updateStatus('Error', 'error');
        } finally {
            this.setLoading(false);
        }
    }

    async callNavigationAPI(prompt) {
        const response = await fetch('/api/route', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: prompt })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    async handleAPIResponse(data, originalPrompt) {
        this.currentRoute = data;
        
        // Extract route information
        const intent = data.intent;
        const waypoints = data.waypoints;

        // Create response message
        let responseMessage = this.formatResponseMessage(intent, waypoints);
        this.addMessage(responseMessage, 'bot');

        // Update map with route
        await this.updateMap(waypoints, intent);
        
        // Update status
        this.updateStatus('Route Generated', 'success');
    }

    formatResponseMessage(intent, waypoints) {
        let message = `🎯 **${intent.intent_type} Route Found!**\n\n`;
        
        message += `📍 **From:** ${intent.origin}\n`;
        message += `📍 **To:** ${intent.destination}\n`;
        message += `🚗 **Mode:** ${intent.travel_modes.join(', ')}\n\n`;

        if (waypoints.waypoints && waypoints.waypoints.length > 0) {
            message += `🗺️ **${waypoints.waypoints.length} waypoints** mapped on the route\n`;
        }

        // Add specific metrics based on route type
        if (waypoints.total_distance_m) {
            const distance = (waypoints.total_distance_m / 1000).toFixed(1);
            message += `📏 **Distance:** ${distance} km\n`;
        }

        if (waypoints.total_duration_s) {
            const duration = Math.round(waypoints.total_duration_s / 60);
            message += `⏱️ **Duration:** ${duration} minutes\n`;
        }

        if (waypoints.calories_burned) {
            message += `🔥 **Calories:** ${Math.round(waypoints.calories_burned)} cal\n`;
        }

        if (intent.constraints && intent.constraints.length > 0) {
            message += `✨ **Features:** ${intent.constraints.join(', ')}\n`;
        }

        return message;
    }

    async updateMap(waypoints, intent) {
        // Clear existing markers and routes
        this.clearMap();

        if (!waypoints.waypoints || waypoints.waypoints.length === 0) {
            this.updateMapInfo('No waypoints available for this route');
            return;
        }

        const points = waypoints.waypoints;
        
        if (points.length >= 2) {
            // Create route with waypoints
            const origin = new google.maps.LatLng(points[0].lat, points[0].lng);
            const destination = new google.maps.LatLng(points[points.length - 1].lat, points[points.length - 1].lng);
            
            // Intermediate waypoints
            const waypointsArray = points.slice(1, -1).map(point => ({
                location: new google.maps.LatLng(point.lat, point.lng),
                stopover: true
            }));

            // Request directions
            const request = {
                origin: origin,
                destination: destination,
                waypoints: waypointsArray,
                travelMode: this.getTravelMode(intent.travel_modes[0]),
                optimizeWaypoints: intent.optimize_waypoints || false
            };

            this.directionsService.route(request, (result, status) => {
                if (status === 'OK') {
                    this.directionsRenderer.setDirections(result);
                    this.addCustomMarkers(points);
                    this.updateMapInfo(`Showing ${intent.intent_type.toLowerCase()} route with ${points.length} stops`);
                } else {
                    // Fallback to markers only
                    this.addMarkersOnly(points);
                    this.updateMapInfo(`Showing ${points.length} waypoints (route display unavailable)`);
                }
            });
        } else {
            // Single point - just add marker
            this.addMarkersOnly(points);
            this.updateMapInfo('Showing location marker');
        }

        // Fit map to show all points
        this.fitMapToPoints(points);
    }

    addCustomMarkers(points) {
        points.forEach((point, index) => {
            let icon, title;
            
            if (index === 0) {
                icon = '🚀'; // Start
                title = `Start: ${point.name}`;
            } else if (index === points.length - 1) {
                icon = '🏁'; // End
                title = `Destination: ${point.name}`;
            } else {
                icon = '📍'; // Waypoint
                title = `Stop ${index}: ${point.name}`;
            }

            const marker = new google.maps.Marker({
                position: { lat: point.lat, lng: point.lng },
                map: this.map,
                title: title,
                label: {
                    text: icon,
                    fontSize: '20px'
                }
            });

            // Add info window
            const infoWindow = new google.maps.InfoWindow({
                content: `<div style="color: #333;"><strong>${title}</strong><br>${point.name}</div>`
            });

            marker.addListener('click', () => {
                infoWindow.open(this.map, marker);
            });

            this.markers.push(marker);
        });
    }

    addMarkersOnly(points) {
        points.forEach((point, index) => {
            const marker = new google.maps.Marker({
                position: { lat: point.lat, lng: point.lng },
                map: this.map,
                title: point.name,
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    scale: 10,
                    fillColor: '#76b900',
                    fillOpacity: 1,
                    strokeColor: '#ffffff',
                    strokeWeight: 2
                }
            });

            const infoWindow = new google.maps.InfoWindow({
                content: `<div style="color: #333;"><strong>${point.name}</strong></div>`
            });

            marker.addListener('click', () => {
                infoWindow.open(this.map, marker);
            });

            this.markers.push(marker);
        });
    }

    fitMapToPoints(points) {
        if (points.length === 0) return;

        const bounds = new google.maps.LatLngBounds();
        points.forEach(point => {
            bounds.extend(new google.maps.LatLng(point.lat, point.lng));
        });

        this.map.fitBounds(bounds);
        
        // Ensure minimum zoom level
        google.maps.event.addListenerOnce(this.map, 'bounds_changed', () => {
            if (this.map.getZoom() > 15) {
                this.map.setZoom(15);
            }
        });
    }

    getTravelMode(mode) {
        const modes = {
            'driving': google.maps.TravelMode.DRIVING,
            'walking': google.maps.TravelMode.WALKING,
            'bicycling': google.maps.TravelMode.BICYCLING,
            'transit': google.maps.TravelMode.TRANSIT
        };
        return modes[mode] || google.maps.TravelMode.DRIVING;
    }

    clearMap() {
        // Clear markers
        this.markers.forEach(marker => marker.setMap(null));
        this.markers = [];
        
        // Clear directions
        this.directionsRenderer.setDirections({routes: []});
    }

    addMessage(content, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Convert markdown-style formatting to HTML
        const formattedContent = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
            
        contentDiv.innerHTML = formattedContent;
        messageDiv.appendChild(contentDiv);
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    setLoading(isLoading) {
        this.sendButton.disabled = isLoading;
        this.chatInput.disabled = isLoading;
        
        if (isLoading) {
            this.sendIcon.textContent = '⏳';
            this.sendText.innerHTML = '<span class="loading-dots">Processing</span>';
            this.updateStatus('Processing...', 'loading');
        } else {
            this.sendIcon.textContent = '🚀';
            this.sendText.textContent = 'Send';
        }
    }

    updateStatus(message, type = 'success') {
        this.status.textContent = message;
        this.status.className = `status ${type}`;
    }

    updateMapInfo(message) {
        this.mapInfo.textContent = message;
    }
}

        // Initialize the chatbot when the page loads
        document.addEventListener('DOMContentLoaded', () => {
            const chatbot = new NaviChatbot();
            console.log('🚀 MapsAI Chatbot initialized successfully!');
        });

// Add some sample prompts for easy testing
window.samplePrompts = [
    "scenic route from San Francisco to Oakland",
    "fitness walking route in downtown for 30 minutes",
    "fastest route from Berkeley to San Jose",
    "bike route through Golden Gate Park"
]; 