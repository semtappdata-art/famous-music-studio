#!/bin/bash
# MCP Server'larını başlatır

set -e

echo "🚀 MCP Server'lar başlatılıyor..."

# Proje kök dizini
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# MCP server'ları için log klasörü
mkdir -p logs/mcp

echo "🚀 MCP Server'lar başlatılıyor..."

# 1. Filesystem MCP Server
echo "📁 Filesystem MCP Server başlatılıyor..."
npx -y @modelcontextprotocol/server-filesystem "C:/Users/ACER/Desktop/ilk-projem/projects" > logs/mcp/filesystem.log 2>&1 &
FILESYSTEM_PID=$!
echo "  Filesystem MCP PID: $FILESYSTEM_PID"

# 2. Fetch MCP Server
echo "🌐 Fetch MCP Server başlatılıyor..."
npx -y @modelcontextprotocol/server-fetch > logs/mcp/fetch.log 2>&1 &
FETCH_PID=$!
echo "  Fetch MCP PID: $FETCH_PID"

# 3. Memory MCP Server
echo "🧠 Memory MCP Server başlatılıyor..."
npx -y @modelcontextprotocol/server-memory > logs/mcp/memory.log 2>&1 &
MEMORY_PID=$!
echo "  Memory MCP PID: $MEMORY_PID"

# 4. Sequential Thinking MCP Server
echo "🧠 Sequential Thinking MCP Server başlatılıyor..."
npx -y @modelcontextprotocol/server-sequential-thinking > logs/mcp/sequential-thinking.log 2>&1 &
SEQ_PID=$!
echo "  Sequential Thinking MCP PID: $SEQ_PID"

# 5. GitHub MCP Server (eğer GITHUB_TOKEN varsa)
if [ -n "$GITHUB_TOKEN" ]; then
    echo "🐙 GitHub MCP Server başlatılıyor..."
    npx -y @modelcontextprotocol/server-github > logs/mcp/github.log 2>&1 &
    GITHUB_PID=$!
    echo "  GitHub MCP PID: $GITHUB_PID"
else
    echo "⚠️  GITHUB_TOKEN ayarlanmadığı için GitHub MCP atlanıyor"
fi

# 6. SQLite MCP Server
echo "🗄️ SQLite MCP Server başlatılıyor..."
npx -y @modelcontextprotocol/server-sqlite --db-path ./fms.db > logs/mcp/sqlite.log 2>&1 &
SQLITE_PID=$!
echo "  SQLite MCP PID: $SQLITE_PID"

# 5. Chrome DevTools MCP Server
echo "🌐 Chrome DevTools MCP Server başlatılıyor..."
npx -y chrome-devtools-mcp \
  --categoryInput true \
  --categoryNavigation true \
  --categoryEmulation true \
  --categoryPerformance true \
  --categoryNetwork true \
  --categoryDebugging true \
  --categoryExtensions true \
  --categoryExperimentalThirdParty true \
  --categoryMemory true \
  --categoryPerformance true \
  --categoryNetwork true \
  --categoryDebugging true \
  --categoryExperimentalWebmcp true \
  --categoryPwa true \
  --autoConnect true \
  --channel stable \
  --headless false \
  --acceptInsecureCerts true \
  --screenshotFormat jpeg \
  --screenshotQuality 85 > logs/mcp/chrome-devtools.log 2>&1 &
CHROME_PID=$!
echo "  Chrome DevTools MCP PID: $CHROME_PID"

echo ""
echo "✅ Tüm MCP Server'lar başlatıldı!"
echo ""
echo "📋 Çalışan Process'ler:"
echo "  Filesystem: $FILESYSTEM_PID"
echo "  Fetch: $FETCH_PID"
echo "  Memory: $MEMORY_PID"
echo "  Sequential: $SEQ_PID"
echo "  SQLite: $SQLITE_PID"
echo "  Chrome DevTools: $CHROME_PID"
if [ -n "$GITHUB_PID" ]; then
  echo "  GitHub: $GITHUB_PID"
fi
echo ""
echo "📋 Log dosyaları: logs/mcp/ klasöründe"
echo ""
echo "🛑 Durdurmak için: kill $FILESYSTEM_PID $FETCH_PID $MEMORY_PID $SEQ_PID $SQLITE_PID $CHROME_PID ${GITHUB_PID:-}"

# PID'leri dosyaya kaydet (sonra kill için)
cat > .mcp_pids << EOF
FILESYSTEM=$FILESYSTEM_PID
FETCH=$FETCH_PID
MEMORY=$MEMORY_PID
SEQUENTIAL=$SEQ_PID
SQLITE=$SQLITE_PID
CHROME=$CHROME_PID
GITHUB=${GITHUB_PID:-}
EOF

echo ""
echo "✅ Tüm MCP Server'lar başarıyla başlatıldı!"
echo "Loglar: tail -f logs/mcp/*.log"
echo "Durdurmak için: kill \$(cat .mcp_pids | cut -d'=' -f2 | tr '\n' ' ')"