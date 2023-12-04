// bookmarklet.js
(function () {
    (window.bookmarkletMFC = function () {

        const MFC_URL = localStorage.getItem('MFM_baseurl')
        const MFC_FLEET_INDEX_URL = `${MFC_URL}/fleets/index`
        const MFC_SERVER_ADD_URL = `${MFC_URL}/servers/add`

        const DEFAULT_SERVER_NAME = window.location.origin
        const token = localStorage.getItem('MFM_token')
        const token_type = localStorage.getItem('MFM_token_type')

        /** API MFC */
        async function getFleetIndex() {
            const response = await fetch(MFC_FLEET_INDEX_URL, {
                headers: {
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json",
                    "Authorization": `${token_type} ${token}`
                },
                method: 'GET',
            })
            return response.json()
        }

        async function addServer(fleetID, serverData) {
            const url = `${MFC_SERVER_ADD_URL}/${fleetID}`
            // console.debug(`Posting to ${url}`);
            // console.debug(serverData);
            const response = await fetch(url, {
                headers: {
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": `${token_type} ${token}`
                },
                method: 'POST',
                body: JSON.stringify(serverData)
            })
            return response.json()
        }

        /** API MISP */
        async function fetchInstanceInfo() {
            const fullApiKey = await createApiKey()
            // const fullApiKey = { AuthKey: { authkey_raw: 'qwertyuiop123456789' } }
            data = {
                url: window.location.origin,
                apiKey: fullApiKey.AuthKey.authkey_raw,
            }
            return data
        }

        function buildServerQuery(instanceInfo) {
            return {
                name: instanceInfo.server_name,
                url: instanceInfo.url,
                authkey: instanceInfo.apiKey,
                comment: 'Created with bookmarklet',
            }
        }

        async function getUser() {
            const url = "/users/view/me.json"
            const response = await fetch(url, {
                headers: { "Content-Type": "application/json; charset=utf-8" },
            })
            return response.json()
        }

        async function checkIfMISP() {
            const url = "/css/action_table.css"
            const response = await fetch(url)
            return response.ok && !response.redirected
        }

        async function createApiKey() {
            const url = "/auth_keys/add/me"
            const response = await fetch(url, {
                headers: { "Content-Type": "application/json; charset=utf-8", "Accept": "application/json" },
                method: 'POST',
                body: JSON.stringify({
                    AuthKey: {
                        comment: 'Authkey for MFC',
                        read_only: 0,
                        allowed_ips: '',
                        expiration: '',
                    }
                })
            })
            return response.json()
        }

        /** Helpers */
        function isUserAdmin(user) {
            return user.Role.perm_site_admin
        }

        /** UI */
        function createModal() {
            const modalContainer = document.createElement("div")
            modalContainer.id = 'MFC_MODAL'
            modalContainer.style.display = 'none'
            modalContainer.style.position = 'fixed'
            modalContainer.style.top = 0
            modalContainer.style.left = 0
            modalContainer.style.width = '100%'
            modalContainer.style.height = '100%'
            modalContainer.style['z-index'] = '2000'
            modalContainer.style.background = '#00000088'

            const modal = document.createElement("div")
            modal.style.position = 'relative'
            modal.style['max-width'] = '600px'
            modal.style['min-height'] = '400px'
            modal.style.width = 'auto'
            modal.style.margin = '2rem auto'
            modal.style.background = '#fff'
            modal.style.color = '#000'
            modal.style.border = '1px solid #ccc'
            modal.style['border-radius'] = '0.25rem'
            modal.style['box-shadow'] = '0 0.5rem 1rem #00000033;'

            /* Header */
            const modalHeader = document.createElement("div")
            modalHeader.classList.add('modal-header')
            modalHeader.style.padding = '0.5rem 1rem'
            modalHeader.style.display = 'flex'
            modalHeader.style['flex-shrink'] = 0
            modalHeader.style['align-items'] = 'center'
            modalHeader.style['justify-content'] = 'space-between;'
            modalHeader.style['font-size'] = '1.25rem'
            modalHeader.style['border-bottom'] = '1px solid #33333355'

            const modalTitle = document.createElement("h3")
            modalHeader.classList.add('modal-title')
            modalTitle.style.margin = 0
            modalTitle.innerText = 'Register server in MISP Fleet Commander'

            const closeBtn = document.createElement("button")
            closeBtn.style.position = 'relative'
            closeBtn.style.width = '1em'
            closeBtn.style.height = '1em'
            closeBtn.style.padding = '.25em .25em'
            closeBtn.style.color = '#000'
            closeBtn.style.background = "transparent url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='%23000'%3e%3cpath d='M.293.293a1 1 0 0 1 1.414 0L8 6.586 14.293.293a1 1 0 1 1 1.414 1.414L9.414 8l6.293 6.293a1 1 0 0 1-1.414 1.414L8 9.414l-6.293 6.293a1 1 0 0 1-1.414-1.414L6.586 8 .293 1.707a1 1 0 0 1 0-1.414z'/%3e%3c/svg%3e\")";
            closeBtn.style.border = 0
            closeBtn.style['border-radius'] = '.375rem'
            closeBtn.style['margin-left'] = 'auto'
            closeBtn.style.cursor = 'pointer'
            closeBtn.onclick = function () { document.getElementById('MFC_MODAL').remove() }

            modalHeader.appendChild(modalTitle)
            modalHeader.appendChild(closeBtn)
            modal.appendChild(modalHeader)

            /* body */
            const modalBody = document.createElement("div")
            modalBody.classList.add('modal-body')
            modalBody.style.padding = '1rem'
            modalBody.style['font-size'] = '1rem'

            modal.appendChild(modalBody)

            modalContainer.appendChild(modal)
            document.body.appendChild(modalContainer)
        }

        function showModal() {
            document.getElementById('MFC_MODAL').style.display = 'block'
        }
        function removeModal() {
            document.getElementById('MFC_MODAL').remove()
        }

        function getTitleElem() {
            return document.querySelector('#MFC_MODAL .modal-body-title')
        }
        function getBodyElem() {
            return document.querySelector('#MFC_MODAL .modal-body')
        }

        async function askImportOptions() {
            // Fleet
            const bodyElem = getBodyElem()
            let fleets = await getFleetIndex()
                .catch((error) => {
                    alert('Could not fetch available fleets from MFC.\n' + error)
                })
            if (fleets === undefined) {
                // fleets = [{ name: 'fleet 1', id: 1 }, { name: 'fleet 2', id: 2 }]
                return
            }
            const fleetIDContainer = document.createElement("div")
            fleetIDContainer.classList.add('modal-fleet-id-container')
            const fieldSetFleet = document.createElement("fieldset")
            const legendFleet = document.createElement("legend")
            legendFleet.style['margin-bottom'] = '0'
            legendFleet.style['border-bottom'] = 'unset'
            legendFleet.style['font-size'] = '1rem'
            legendFleet.style['line-height'] = '2rem'
            fieldSetFleet.appendChild(legendFleet)
            legendFleet.innerText = 'Select the fleet on which to add the server:'
            fleets.forEach(fleet => {
                let fleetContainer = document.createElement("div")
                let fleetIDInput = document.createElement("input")
                fleetIDInput.type = 'radio'
                fleetIDInput.id = fleet.id
                fleetIDInput.name = 'fleet_id'
                fleetIDInput.value = fleet.id
                let fleetLabel = document.createElement("label")
                fleetLabel.htmlFor = fleet.id
                fleetLabel.innerText = fleet.name
                fleetLabel.style.display = 'inline-block'
                fleetLabel.style['margin-left'] = '0.25rem'
                fleetContainer.appendChild(fleetIDInput)
                fleetContainer.appendChild(fleetLabel)
                fieldSetFleet.appendChild(fleetContainer)
            });
            fleetIDContainer.appendChild(fieldSetFleet)
            bodyElem.appendChild(fleetIDContainer)

            // Instance name
            let fleetNameLabel = document.createElement("label")
            fleetNameLabel.for = 'server_name'
            fleetNameLabel.innerText = 'Server name: '
            let fleetNameInput = document.createElement("input")
            fleetNameInput.type = 'text'
            fleetNameInput.name = 'server_name'
            fleetNameInput.id = 'server_name'
            fleetNameInput.value = DEFAULT_SERVER_NAME
            fleetNameInput.style.width = "95%"
            fleetNameLabel.appendChild(fleetNameInput)
            bodyElem.appendChild(fleetNameLabel)

            // Import buttons
            const importButtonContainer = document.createElement('div')
            const importBtn = document.createElement("button")
            importBtn.style['background-color'] = 'blue'
            importBtn.style['color'] = 'white'
            importBtn.innerText = 'Import server'
            importBtn.onclick = function () { doImport() }
            importButtonContainer.appendChild(importBtn)
            bodyElem.appendChild(importButtonContainer)

            showModal()
        }

        function askUserNotAdmin(user) {
            return confirm(`Current user is not an admin user! Proceed to add this instance with the current user (Role: ${user.Role.name}) ?`)
        }

        async function doImport() {
            const fleetID = document.querySelector('#MFC_MODAL .modal-body input:checked').value
            const serverName = document.querySelector('#MFC_MODAL .modal-body input#server_name').value

            const instanceInfo = await fetchInstanceInfo()
            instanceInfo.server_name = serverName
            const serverData = buildServerQuery(instanceInfo)

            addServer(fleetID, serverData)
                .then((data) => {
                    alert(data.url !== undefined ? 'Successfully registered server!' : data)
                    removeModal()
                })
                .catch((error) => {
                    alert('Could not import server')
                    console.error(error)
                    console.error('Collected info:')
                    console.error(instanceInfo)
                })
        }

        async function startImport() {
            const isMISP = await checkIfMISP()
            if (!isMISP) {
                alert('It looks like you\'re not on a MISP page. Try again while logged-in in MISP!')
                return
            }
            const user = await getUser()
            let proceed = false
            if (!user.Role) {
                alert('Could not get logged user. Make sure you\'re logged in and viewing a MISP page!')
                return
            }
            createModal()
            if (isUserAdmin(user)) {
                proceed = true
            } else {
                proceed = askUserNotAdmin(user)
            }

            if (!proceed) {
                return
            }
            askImportOptions()
        }

        startImport()

    })();
})();