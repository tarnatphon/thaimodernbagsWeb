# Thai Modern Bags

A responsive corporate landing page, a local-only Ollama SEO drafting workspace, and a manually approved SFTP deploy script for macOS.

For your Mac, keep the project at `/Users/ekky/Documents/thaimodernbags`. In Terminal, run `cd /Users/ekky/Documents/thaimodernbags` once before using the commands below (not `cd cd`). This folder must contain the project files and be your Git checkout; the Arena sandbox at `/home/user/thaimodernbagsWeb` is a separate machine and cannot access your Mac's filesystem directly.

## Preview the website

From the project folder, run:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Run the private Ollama SEO helper

1. Install [Ollama](https://ollama.com/) on your Mac and start it.
2. In Terminal, download a small starter model:

   ```bash
   ollama pull llama3.2:3b
   ```

3. From the project folder, start the helper:

   ```bash
   python3 tools/seo_assistant.py
   ```

4. Open `http://127.0.0.1:8765`.

The helper sends the homepage text and your business notes to Ollama running on your own computer. It drafts suggested page titles, descriptions, content improvements, E-E-A-T evidence ideas, fact-check questions, and structured-data recommendations. It does **not** edit or publish the website. Verify every suggestion and add real first-hand evidence before publishing; no tool can guarantee a first-page Google ranking.

## Configure approved SFTP publishing on macOS

The deploy script uploads only `index.html`, `styles.css`, `script.js`, and `public/images/hero-bags.jpg`. It does not upload the local AI helper or anything in `tools/`. Before uploading, it asks you to type `DEPLOY` and downloads existing copies of those files into a local backup folder. It never asks for or stores your hosting password or private key.

1. In cPanel, enable SSH access and authorize an SSH key if your hosting provider requires it. Ask your host for the SFTP hostname, port, account username, and the website's document-root folder. Keep the private key on your Mac; never put it in this project or give it to the AI.
2. If you do not already have a key for this host, create one in Terminal:

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/tmb_cpanel -C "Thai Modern Bags cPanel"
   ```

   Add the **public** key (`~/.ssh/tmb_cpanel.pub`) through cPanel's SSH key manager and authorize it. Do not share the private key (`~/.ssh/tmb_cpanel`).
3. Add a host alias to `~/.ssh/config`, replacing the example values with those from your hosting provider:

   ```sshconfig
   Host tmb-web
     HostName sftp.example.com
     User CPANEL_USERNAME
     Port 22
     IdentityFile ~/.ssh/tmb_cpanel
     IdentitiesOnly yes
   ```

   Keep this config on your Mac. Test the connection with `sftp tmb-web` and verify the server's host-key prompt with your provider before accepting it.
4. From the project folder, run:

   ```bash
   bash tools/deploy_sftp.sh
   ```

   Enter the SSH alias `tmb-web`, then the correct remote document-root path (often `public_html`, but confirm with your host). Review the file list and type `DEPLOY` only when ready.

The local SEO helper binds to `127.0.0.1`; it is not a public admin panel and should never be uploaded to cPanel. The public site's contact link currently opens a draft email without a recipient; replace it in `index.html` with the business's preferred contact email before publishing.
