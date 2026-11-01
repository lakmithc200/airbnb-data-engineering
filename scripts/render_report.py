"""Local PDF QA helper, requires pypdfium2 and Pillow (not runtime dependencies)."""
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageOps, ImageDraw

root=Path(__file__).resolve().parents[1]
out=root/'tmp/pdfs/report'
out.mkdir(parents=True,exist_ok=True)
doc=pdfium.PdfDocument(str(root/'outputs/albany/2026-09-14/market_report.pdf'))
thumbs=[]
for i in range(len(doc)):
    image=doc[i].render(scale=1.25).to_pil().convert('RGB')
    image.save(out/f'page-{i+1:02d}.png')
    thumb=ImageOps.contain(image,(330,465))
    tile=Image.new('RGB',(350,500),'#d9e1e4')
    tile.paste(thumb,((350-thumb.width)//2,10))
    ImageDraw.Draw(tile).text((12,480),f'Page {i+1}',fill='black')
    thumbs.append(tile)
for start in range(0,len(thumbs),12):
    sheet=Image.new('RGB',(1400,1500),'white')
    for j,img in enumerate(thumbs[start:start+12]):sheet.paste(img,((j%4)*350,(j//4)*500))
    sheet.save(out/f'contact-{start//12+1}.png')
print(f'Rendered {len(doc)} pages to {out}')
