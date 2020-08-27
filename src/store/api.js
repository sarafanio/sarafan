class SarafanAppBackend {
    constructor(backend_url) {
        console.log("Start with backend", backend_url)
        this.backend_url = backend_url
        this.fetchPosts = this.fetchPosts.bind(this);
        this.createPost = this.createPost.bind(this);
        this.publishPost = this.publishPost.bind(this);
        this.authenticate = this.authenticate.bind(this);
    }
    async fetchPosts(cursor) {
        let url = this.backend_url + 'api/posts';
        if (cursor) {
            url += '?cursor=' + cursor
        }
        const resp = await fetch(url, { method: "GET" })
        const data = await resp.json()
        return data
    }
    async createPost(text) {
        let data = {
            text: text,
        }
        const resp = await fetch(this.backend_url + 'api/create_post', { 
            method: "POST",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        return await resp.json();
    }
    async publishPost(magnet, privateKey) {
        const data = {
            magnet: magnet,
            privateKey: privateKey,
        }
        const resp = await fetch(this.backend_url + 'api/publish', { 
            method: "POST",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        return await resp.json();
    }

    async authenticate(private_key) {
        const data = {
            private_key: private_key
        }
        const resp = await fetch(this.backend_url + 'api/authenticate', {
            method: "POST",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        return await resp.json()
    }
}

const api = new SarafanAppBackend("http://localhost:9231/");

export default api;
