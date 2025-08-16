<div align="center">

# 🌪️ Vaayu

### *The Air Element for SSH File Transfers*

**Modern • Secure • Parallel • Resumable**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![SSH/SFTP](https://img.shields.io/badge/Protocol-SSH%2FSFTP-orange.svg)](https://www.openssh.com/)

*Vaayu is the next-generation SSH file transfer tool that moves your data like air—fast, light, and omnipresent.*

</div>

---

## ✨ Why Vaayu?

**Vaayu** (Sanskrit: वायु) means "air"—the element that flows everywhere with speed and grace. Just as air adapts to any environment while maintaining its essential properties, Vaayu delivers files across networks with uncompromising reliability and performance.

### 🚀 Core Capabilities

| Feature | Description |
|---------|-------------|
| **🔒 Secure by Design** | Modern SSH ciphers (ChaCha20-Poly1305, AES-256-GCM) with optional strict host key verification |
| **⚡ Lightning Fast** | Parallel transfers with intelligent concurrency auto-tuning |
| **🔄 Bulletproof Resume** | Atomic writes with `.part` files and intelligent offset recovery |
| **🛡️ Data Integrity** | SHA-256 verification with robust remote fallback chains |
| **🎯 Smart Operations** | Recursive directory sync, wildcard matching, and real-time progress |
| **👁️ Live Monitoring** | Watch mode for continuous synchronization |
| **🌐 Universal** | Windows, macOS, Linux (Python 3.9+) |

### 📡 Transfer Modes

- **📤 Send** — Local → Remote with recursive directory support
- **📥 Get** — Remote → Local with wildcard expansion
- **🔄 Relay** — Remote → Remote without local download

---

## 🏗️ Architecture

Built on enterprise-grade foundations:

- **AsyncIO + AsyncSSH** — High-performance asynchronous I/O
- **Rich Progress** — Beautiful terminal UI with real-time metrics
- **Watchdog** — Filesystem monitoring for live sync
- **zstd** — Optional compression pipeline (future enhancement)

---

## 🚀 Quick Start

### Installation

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

**macOS/Linux (Bash)**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Verify Installation
```bash
vaayu --help
```

---

## 📚 Command Reference

### Global Options

| Short | Long | Description |
|-------|------|-------------|
| `-h` | `--help` | Show help message |
| `-p` | `--port` | SSH port (default: 22) |
| `-u` | `--username` | SSH username |
| `-P` | `--password` | SSH password |
| `-i` | `--identity` | Path to private key |
| `-j` | `--parallel` | Parallel transfer jobs |
| `-r` | `--retries` | Max retries per file (default: 5) |
| `-b` | `--backoff` | Initial backoff seconds (default: 0.5) |
| `-c` | `--compress` | Enable compression |
| `-z` | `--zstd-level` | Compression level (default: 3) |
| `-k` | `--verify-host-key` | Strict host key verification |
| `-n` | `--no-verify` | Skip hash verification |

### Commands

| Command | Description |
|---------|-------------|
| `send` | Transfer files from local to remote |
| `get` | Transfer files from remote to local |
| `relay` | Transfer files between two remote hosts |

---

## 💼 Usage Examples

### 📤 Send Operations

**Basic File Upload**
```bash
vaayu -u alice -i ~/.ssh/id_ed25519 send alice@server.com /remote/backup file.txt
```

**Recursive Directory Upload**
```bash
vaayu -u alice -i ~/.ssh/id_ed25519 send alice@server.com /remote/backup /local/project/
```

**Wildcard Upload with High Parallelism**
```bash
vaayu -u alice -i ~/.ssh/id_ed25519 -j 16 send alice@server.com /remote/logs *.log
```

**Password Authentication**
```bash
vaayu -u alice -P mypassword send alice@server.com /remote/backup document.pdf
```

**Custom Port and Strict Host Key Verification**
```bash
vaayu -u alice -p 2222 -k -i ~/.ssh/id_ed25519 send alice@server.com /backup file.txt
```

**Multiple Files and Directories**
```bash
vaayu -u alice -i ~/.ssh/id_ed25519 send alice@server.com /backup file1.txt dir1/ *.csv
```

**Live Watch Mode**
```bash
vaayu -u alice -i ~/.ssh/id_ed25519 send alice@server.com /remote/www /local/website/ -W
```

### 📥 Get Operations

**Basic File Download**
```bash
vaayu -u bob -i ~/.ssh/id_ed25519 get bob@server.com /local/downloads /remote/file.txt
```

**Wildcard Download**
```bash
vaayu -u bob -i ~/.ssh/id_ed25519 get bob@server.com /local/logs /var/log/*.log
```

**Recursive Directory Download**
```bash
vaayu -u bob -i ~/.ssh/id_ed25519 get bob@server.com /local/backup /remote/project/
```

**Multiple Remote Paths**
```bash
vaayu -u bob -i ~/.ssh/id_ed25519 get bob@server.com /local/data /remote/file1.txt /remote/dir/ /remote/*.csv
```

**High Concurrency Download**
```bash
vaayu -u bob -i ~/.ssh/id_ed25519 -j 32 get bob@server.com /local/download /remote/bigdata/
```

### 🔄 Relay Operations

**Direct Remote-to-Remote Transfer**
```bash
vaayu -u admin -i ~/.ssh/id_ed25519 relay admin@source.com admin@dest.com /data/file.txt /backup/file.txt
```

**Multiple File Relay**
```bash
vaayu -u admin -i ~/.ssh/id_ed25519 relay admin@source.com admin@dest.com /data/file1.txt /data/file2.txt /backup/file1.txt /backup/file2.txt
```

**Cross-Server Directory Sync**
```bash
vaayu -u admin -i ~/.ssh/id_ed25519 relay admin@prod.com admin@backup.com /var/www/ /backups/www/
```

### ⚙️ Advanced Usage

**Resume Interrupted Transfer**
```bash
vaayu -u alice -i ~/.ssh/id_ed25519 send alice@server.com /remote/backup largefile.zip
```

**Skip Verification for Trusted Networks**
```bash
vaayu -u alice -i ~/.ssh/id_ed25519 -n send alice@server.com /remote/backup *.txt
```

**Custom Retry Strategy**
```bash
vaayu -u alice -i ~/.ssh/id_ed25519 -r 10 -b 1.0 send alice@server.com /backup file.txt
```

**Compression Enabled**
```bash
vaayu -u alice -i ~/.ssh/id_ed25519 -c -z 6 send alice@server.com /backup archive.tar
```

---

## 🔧 Performance Tuning

### Parallelism Guidelines

| File Count | Recommended `-j` | Use Case |
|------------|------------------|----------|
| 1-10 | 2-4 | Large files |
| 10-100 | 4-8 | Mixed workload |
| 100-1000 | 8-16 | Many small files |
| 1000+ | 16-32 | Massive parallel I/O |

### Network Optimization

```bash
vaayu -u user -j 8 -r 3 -b 0.2 send user@host /dest /large/dataset/
```

---

## 🛡️ Security Features

### Authentication Methods

- **SSH Key Authentication** (Recommended)
- **Password Authentication**
- **SSH Agent Support**

### Encryption Standards

- **ChaCha20-Poly1305@openssh.com** (Primary)
- **AES-256-GCM@openssh.com** (Fallback)

### Data Integrity

- **SHA-256 Verification** (Default)
- **Atomic Writes** (`.part` → rename)
- **Multiple Remote Hash Sources**

---

## 🏥 Error Handling & Recovery

### Automatic Recovery Features

- **Resume from Interruption** — Continues from last byte
- **Exponential Backoff** — Smart retry timing
- **Hash Verification** — Detects corruption
- **Atomic Operations** — No partial writes

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Connection timeout | Increase `-r` retries and `-b` backoff |
| Permission denied | Check SSH key permissions and remote path access |
| Hash mismatch | Network corruption; transfer will auto-retry |
| Host key verification failed | Use `-k` flag with proper known_hosts |

---

## 🧪 Testing & Validation

### Run Test Suite
```bash
pytest -q
```

### Feature Validation Commands

**Resume Testing**
```bash
vaayu -u user send user@host /dest largefile.bin
```

**Verification Testing**
```bash
vaayu -u user send user@host /dest testfile.txt
sha256sum testfile.txt
ssh user@host "sha256sum /dest/testfile.txt"
```

**Performance Testing**
```bash
time vaayu -u user -j 16 send user@host /dest /large/dataset/
```

---

## 📊 Project Structure

```
vaayu/
├── cli.py           # Command-line interface
├── ssh_client.py    # AsyncSSH wrapper
├── transfer.py      # Core transfer logic
├── verify.py        # Hash verification
├── utils.py         # Utilities and helpers
├── watch.py         # Filesystem monitoring
├── compress.py      # Compression (future)
└── cloud.py         # Cloud protocols (future)
```

---

## 🗺️ Roadmap

### Upcoming Features

- 🗜️ **In-stream zstd compression**
- 🔍 **Enhanced remote hash detection**
- 📄 **Configuration file support**
- 🌩️ **Cloud provider integration**
- 📈 **Advanced performance metrics**
- 🔐 **Certificate-based authentication**

---

## 🤝 Contributing

We welcome contributions! Please check out our development setup:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -e .[dev]
pytest
```

---

## 📄 License

Released under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ for the SSH community**

*Vaayu — Where files flow like air*

---

> 📝 **Note**: This README was generated with AI assistance because the developer was too lazy to write comprehensive documentation (but smart enough to make AI do it properly). 😴✨

</div>
