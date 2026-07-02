// 大數字縮寫：47688427 -> "47.7M"，1781 -> "1.8K"，1200000000 -> "1.2B"
// token 數字都很長，表格/圖表用縮寫比較好讀。
export function abbr(n) {
  if (n == null) return ''
  const x = Number(n)
  if (!isFinite(x)) return ''
  const sign = x < 0 ? '-' : ''
  const a = Math.abs(x)
  if (a >= 1e9) return sign + (a / 1e9).toFixed(1).replace(/\.0$/, '') + 'B'
  if (a >= 1e6) return sign + (a / 1e6).toFixed(1).replace(/\.0$/, '') + 'M'
  if (a >= 1e3) return sign + (a / 1e3).toFixed(1).replace(/\.0$/, '') + 'K'
  return String(x)
}

// tooltip 用的完整數字（加千分位）：47688427 -> "47,688,427"
export function full(n) {
  if (n == null) return '—'
  return Number(n).toLocaleString('en-US')
}

// 顯示名稱：有正常姓名就用姓名；姓名是 email（或空）就取 @ 前面那段。
// 例：name="Chloe Shy" -> "Chloe Shy"；name="qshericzhu@iei.com.tw ..." -> "qshericzhu"
export function displayName(name, email) {
  const n = (name || '').trim()
  const e = (email || '').trim()
  // name 為空、或 name 本身就是（含重複的）email，就退回取 email 前綴
  if (!n || n.includes('@')) {
    return e ? e.split('@')[0] : n
  }
  return n
}

// YYYY-MM-DD -> MM/DD（矩陣欄位標頭用）
export function shortDate(d) {
  if (!d) return ''
  const [, m, day] = d.split('-')
  return `${m}/${day}`
}
