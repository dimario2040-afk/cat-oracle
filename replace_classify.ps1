$content = Get-Content -Path bot.py -Raw
# Pattern to match the classify_cat function up to the next function definition (def analyze_audio_bytes)
$pattern = '(?s)(def classify_cat\(rms, f0\):.*?)(?=\r?\n\s*def analyze_audio_bytes)'
$replacement = @'
def classify_cat(rms, f0):
    # Compute similarity score for each cat
    scored = []
    for cat in CATALOGUE:
        a = cat["acoustic"]
        rms_mid = (a["min_rms"] + a["max_rms"]) / 2
        f0_mid = (a["min_f0"] + a["max_f0"]) / 2
        # Normalize differences
        rms_diff = abs(rms - rms_mid) / (a["max_rms"] - a["min_rms"] + 1e-6)
        f0_diff = abs(f0 - f0_mid) / (a["max_f0"] - a["min_f0"] + 1e-6)
        score = rms_diff + f0_diff  # lower is better
        scored.append((score, cat))
    # Sort by score
    scored.sort(key=lambda x: x[0])
    # Take top N (e.g., 10) and pick random weighted by inverse score
    top = scored[:10]
    # Compute weights: higher weight for lower score
    weights = [1.0 / (score + 1e-6) for score, _ in top]
    total = sum(weights)
    probs = [w / total for w in weights]
    chosen = random.choices([cat for _, cat in top], weights=probs)[0]
    return chosen
'@
$newContent = [regex]::Replace($content, $pattern, $replacement)
Set-Content -Path bot.py -Value $newContent -Encoding UTF8
Write-Host "Replaced classify_cat function."