# Generates the MediQueue PWA icons (Windows PowerShell + System.Drawing).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\generate_icons.ps1
Add-Type -AssemblyName System.Drawing

function New-MediQueueIcon {
    param(
        [Parameter(Mandatory = $true)][int]$Size,
        [Parameter(Mandatory = $true)][string]$Path,
        [double]$GlyphScale = 0.42
    )

    $bitmap = [System.Drawing.Bitmap]::new($Size, $Size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

    $rect = [System.Drawing.Rectangle]::new(0, 0, $Size, $Size)
    $brush = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
        $rect,
        [System.Drawing.Color]::FromArgb(15, 118, 110),
        [System.Drawing.Color]::FromArgb(17, 94, 89),
        45.0
    )
    $graphics.FillRectangle($brush, $rect)

    $white = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)

    $fontSize = [float]($Size * $GlyphScale)
    $font = [System.Drawing.Font]::new(
        'Segoe UI',
        $fontSize,
        [System.Drawing.FontStyle]::Bold,
        [System.Drawing.GraphicsUnit]::Pixel
    )
    $format = [System.Drawing.StringFormat]::new()
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $textRect = [System.Drawing.RectangleF]::new(0, 0, [float]$Size, [float]($Size * 0.82))
    $graphics.DrawString('M', $font, $white, $textRect, $format)

    $dotRadius = [int]($Size * 0.045)
    $gap = [int]($Size * 0.11)
    $centerX = [int]($Size / 2)
    $y = [int]($Size * 0.78)
    for ($index = -1; $index -le 1; $index++) {
        $x = $centerX + ($index * $gap) - $dotRadius
        $graphics.FillEllipse($white, $x, $y, $dotRadius * 2, $dotRadius * 2)
    }

    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
    $brush.Dispose()
    $white.Dispose()
    $font.Dispose()
    $format.Dispose()
}

$iconsDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'static\icons'
New-Item -ItemType Directory -Force -Path $iconsDir | Out-Null
New-MediQueueIcon -Size 192 -Path (Join-Path $iconsDir 'icon-192.png')
New-MediQueueIcon -Size 512 -Path (Join-Path $iconsDir 'icon-512.png')
New-MediQueueIcon -Size 512 -Path (Join-Path $iconsDir 'icon-512-maskable.png') -GlyphScale 0.34
Write-Host "Icons written to $iconsDir"
