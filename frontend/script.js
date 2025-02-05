document.addEventListener('DOMContentLoaded', function() {
    const uploadButton = document.getElementById('uploadButton');
    const csvFile = document.getElementById('csvFile');
    const uploadStatus = document.getElementById('uploadStatus');
    const deviceList = document.getElementById('deviceList');

    uploadButton.addEventListener('click', function() {
        const file = csvFile.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('csv_file', file);

            fetch('/api/upload-csv', { // Assuming Flask backend is running on same domain/port for now
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (response.ok) {
                    uploadStatus.textContent = data.message;
                    uploadStatus.style.color = 'green';
                    loadDevices(); // Reload device list after successful upload
                } else {
                    uploadStatus.textContent = data.message + (data.error ? ` Error: ${data.error}` : '');
                    uploadStatus.style.color = 'red';
                }
            })
            .catch(error => {
                uploadStatus.textContent = 'Error uploading file: ' + error;
                uploadStatus.style.color = 'red';
            });
        } else {
            uploadStatus.textContent = 'Please select a CSV file.';
            uploadStatus.style.color = 'orange';
        }
    });

    function loadDevices() {
        fetch('/api/devices') // Fetch device list from API
        .then(response => response.json())
        .then(data => {
            deviceList.innerHTML = ''; // Clear existing list
            if (data.devices && data.devices.length > 0) {
                data.devices.forEach(device => {
                    const listItem = document.createElement('li');
                    listItem.textContent = `${device.manufacturer} - ${device.device_type} (ID: ${device.id})`;
                    deviceList.appendChild(listItem);
                });
            } else {
                const listItem = document.createElement('li');
                listItem.textContent = 'No devices found.';
                deviceList.appendChild(listItem);
            }
        })
        .catch(error => {
            deviceList.innerHTML = 'Error loading devices: ' + error;
        });
    }

    loadDevices(); // Load devices on page load
});