#!/usr/bin/env bash
# deploy.sh —— 一键部署本目录到 GitHub Pages
# 用法：
#   source /root/.codebuddy/skills/github-connector/scripts/get_token.sh github
#   bash deploy.sh <GitHub用户名> <仓库名>
# 说明：需要有效的 GitHub OAuth Token（环境变量 GITHUB_TOKEN）。脚本不会打印 token。
set -e

OWNER="$1"
REPO="$2"
if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
  echo "用法: bash deploy.sh <GitHub用户名> <仓库名>"
  exit 1
fi
if [ -z "$GITHUB_TOKEN" ]; then
  echo "错误: 未检测到 GITHUB_TOKEN，请先获取 GitHub 授权。"
  exit 1
fi

AUTH="Authorization: Bearer ${GITHUB_TOKEN}"
API="https://api.github.com"

echo "==> 检查仓库 ${OWNER}/${REPO} 是否存在…"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH" "$API/repos/${OWNER}/${REPO}")
if [ "$CODE" = "404" ]; then
  echo "==> 创建远程仓库…"
  curl -s -H "$AUTH" -H "Content-Type: application/json" -X POST "$API/user/repos" \
    -d "{\"name\":\"${REPO}\",\"private\":false,\"description\":\"今天谁离开了我们 · 讣告档案（静态网页版）\"}" > /tmp/gh_create.json
  echo "    创建结果 HTTP: $(curl -s -o /dev/null -w '%{http_code}' -H "$AUTH" "$API/repos/${OWNER}/${REPO}")"
elif [ "$CODE" != "200" ]; then
  echo "错误: 访问仓库失败，HTTP ${CODE}（Token 可能失效）。"
  exit 1
else
  echo "    仓库已存在。"
fi

echo "==> 配置 remote 并推送…"
git remote remove origin 2>/dev/null || true
git remote add origin "https://oauth2:${GITHUB_TOKEN}@github.com/${OWNER}/${REPO}.git"
git branch -M main
git push -u origin main --force

echo "==> 开启 GitHub Pages…"
curl -s -X POST -H "$AUTH" -H "Accept: application/vnd.github+json" \
  "$API/repos/${OWNER}/${REPO}/pages" \
  -d '{"source":{"branch":"main","path":"/"}}' > /tmp/gh_pages.json || true

echo "✅ 部署完成。访问地址："
echo "   https://${OWNER}.github.io/${REPO}/"
echo "（Pages 首次构建可能需要 1-2 分钟）"
