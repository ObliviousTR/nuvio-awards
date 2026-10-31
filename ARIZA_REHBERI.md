# Arıza rehberi (Nuvio otomasyonları)

Bu repo Ozzy'nin Nuvio koleksiyonunu besler. İçinde eklentiler (Awards, Spotlight, Library), koleksiyon paketlerini
üreten `builder/` ve görselleri yenileyen GitHub Actions otomasyonları var. Bu dosya, bir otomasyon bozulduğunda onu
düzeltecek kişi ya da yapay zekâ ajanı içindir. **Herhangi bir değişiklikten önce baştan sona oku.**

## 1. Değişmez kurallar

1. **Anahtarlar yalnızca GitHub Secrets'ta durur.** TMDB, fanart.tv, MDBList, Simkl, Cloudflare ve AIOMetadata anahtarları
   asla koda, commit'e, issue'ya, loga ya da sohbete yazılmaz. Repo herkese açık. Kod anahtarları yalnızca
   `os.environ[...]` ile okur. Bir hata mesajı anahtar içeriyorsa onu kopyalama.
2. **`simkl/token.enc` şifreli Simkl jetonudur.** Elle düzenleme, silme ya da çözmeye çalışma. Home lists ve Favourites
   her çalışmada onu yeniler ve yeniden kaydeder.
3. **`builder/out/delivered/baseline.json` Ozzy'nin Nuvio'daki son hâlidir** (son içe aktardığı paket ya da kendi
   dışa aktarımı). Yeni bir koleksiyon paketi **yalnızca bunun üzerinden**, yalnızca gereken alanları değiştirerek
   üretilir. Sıfırdan üretilen bir paket Ozzy'nin elle yaptığı düzenlemeleri (silinen/sıralanan klasörler, Live
   Sport, kendi eklediği klasörler) geri alır. Paket üretmek gerekirse önce Ozzy'den güncel dışa aktarımını iste.
4. **Paketi Ozzy içe aktarır, sen değil.** Ona neyin değiştiğini söyle; o kontrol edip "Replace" ile alır.
5. **E-posta bildirimi açma** (Ozzy istemiyor). Kişisel bilgi (e-posta, gerçek ad dışındaki bilgiler) repoya girmez.
6. **Lisanssız yayın sitelerinden içerik çeken kazıyıcı/eklenti yazılmaz.**
7. Düzeltmeyi küçük tut: yalnızca bozulan şeyi düzelt, tasarımı (logolar, kapaklar, hero'lar) değiştirme. Tasarım
   kararları Ozzy'nindir.

## 2. Otomasyonlar

Saatler İstanbul saatiyle. GitHub zamanlanmış işleri çoğu zaman saatlerce geciktirir; bu normaldir.

| Otomasyon (Actions'taki adı) | Ne zaman | Ne yapar | Secret'lar |
|---|---|---|---|
| Turkish titles | her gün 05:41 | Türk yapımlarının Türkçe adları (`trmeta/`) | TMDB |
| Spotlight | her gün 06:17 | Spotlight kartları, kapaklar, hover'lar, hero'lar (`spotlight/`) | TMDB |
| Genre rails | her gün 06:23 | Tür rafları (`library/`) | TMDB, MDBList |
| Home lists | her gün 06:47 | Trending Movies/Series ve For You (`library/catalog/*/home-*`) | TMDB, MDBList, Simkl |
| Discover art | Pazartesi 06:37 | Discover kapakları, hero ve logolar → `discover-art` dalı | TMDB |
| Favourites art | Pazartesi 07:17 | Favourites kapakları (Simkl'den) | TMDB, MDBList, Simkl |
| Update award lists | Pazartesi 08:23 | Ödül listeleri, Awards eklentisi | — |
| Library | Pazar 07:41 | Library eklentisi kataloğu | TMDB |
| Network art · Genre art · Mood art · Kids art · Studio art · Awards art · Based On art · Decade art · International art · Reality art · Docs art | her ayın 1'i, 07:41–09:43 | Satırların kapak, hover, TV hero ve logoları → her biri kendi dalına (`network-art`, `genre-art`, `mood-art`, `kids-art`, `studio-art`, `awards-art`, `basedon-art`, `decade-art`, `intl-art`, `reality-art`, `docs-art`) | TMDB, fanart.tv |
| New year | 1 Ocak (ve 1 Mart) | Yıl geçişi paketi `builder/out/delivered/nuvio-<yıl>-ocak|mart.json`; Ozzy içe aktarır | — |
| Simkl link, TR proxy, Parser self-test, Scratch | elle | Kurulum / araç işleri; normalde dokunulmaz | çeşitli |

Görsel dalları (`*-art`) her çalışmada tek commit'le baştan yazılır; Nuvio bu dallardaki sabit adresleri okur
(`<dal>/<klasör>/cover.jpg`, `hover.webp`, `backdrop.jpg`, `logo.png`). Bir aylık otomasyon hata verirse
**bir önceki ayın görselleri kalır**, Nuvio'da boş bir şey görünmez; acil değildir.

Diğer klasörlerin hero ve logoları ayrı `ObliviousTR/nuvio-art` reposunda durur ve elle üretilir
(`art_tools/build_heroes.py` + `art_tools/heroes_spec.json`); orada otomasyon yok.

## 3. Bozulan bir otomasyonu bulmak

1. GitHub → **Actions** → kırmızı (başarısız) çalışmayı aç → kırmızı adımı aç; hata genelde son satırlardadır.
2. Komut satırından: `gh run list --limit 20` ve `gh run view <id> --log-failed`.
3. Düzelttikten sonra aynı otomasyonu Actions'ta **Run workflow** ile elle çalıştır ve yeşil bittiğini gör.

## 4. Sık hatalar ve çözümleri

| Belirti (logda) | Sebep | Çözüm |
|---|---|---|
| `timed out`, `Connection reset`, `HTTP Error 429/500/502/503` | TMDB/fanart.tv/ağ anlık sorunu | **Re-run failed jobs.** Kod değişmez. |
| `TMDB rejected the key (401)` | TMDB anahtarı geçersiz | Ozzy yeni anahtar alır, Settings → Secrets → `TMDB_API_KEY` güncellenir. Koda yazılmaz. |
| fanart.tv ya da MDBList 401/403 | ilgili anahtar geçersiz | `FANART_API_KEY` / `MDBLIST_API_KEY` secret'ını Ozzy yeniler. |
| `Simkl refresh failed` | Simkl bağlantısı düşmüş (yenileme jetonu ~180 gün) | Actions → **Simkl link** → Run workflow; logda değil `design-refs` dalında `refs/simkl/code.txt` içindeki kodu Ozzy simkl.com/pin'de onaylar. |
| `ModuleNotFoundError: No module named 'X'` | iş, ihtiyaç duyduğu Python paketini kurmuyor | İlgili `.github/workflows/<ad>.yml` içindeki `pip install` satırına paketi ekle (ör. `numpy`, `scipy`, `opencv-python-headless`). Liste işleri (Genre rails, Home lists, Library) `scripts/spotlight.py`'yi içe aktarır; oradaki görsel modüller `try/except ImportError` içinde, öyle kalmalı. |
| `rejected ... non-fast-forward` / `failed to push` | aynı anda başka bir iş `main`'e yazdı | Re-run. İşler `concurrency: repo-writes` ve `git pull --rebase` kullanır. |
| İş hiç çalışmıyor, Actions'ta "disabled" | GitHub 60 gün hareketsiz repolarda zamanlamayı kapatır | Actions → ilgili iş → **Enable workflow**. |
| Bir klasörün görseli eksik/bozuk ama iş yeşil | o klasörün kaynağında (TMDB) sorun | O iş "build.log"/log çıktısında klasör adını ara; genelde bir sonraki ay kendiliğinden düzelir. Tasarımı değiştirme, Ozzy'ye bildir. |

## 5. Yerelde denemek

```
pip install pillow numpy scipy opencv-python-headless cairosvg
export TMDB_API_KEY=...        # yalnız kendi ortamında; asla commit'leme
python3 art_tools/kids_art.py /tmp/out      # aylık işler tek bir klasöre yazar
python3 scripts/genre_rails.py              # liste işleri repo içine yazar; commit'lemeden önce `git diff` ile bak
```

Önizleme: `art_tools/tv_sim.py` içindeki `partial(hero, logo)` Nuvio TV'deki hero + logo görünümünü taklit eder.

## 6. Bitirirken

- Değişikliği küçük bir commit'le `main`'e al; mesajda neyin neden bozulduğunu yaz.
- Düzeltilen otomasyonu elle bir kez çalıştırıp yeşil bittiğini doğrula.
- Ozzy'ye iki-üç cümleyle ne olduğunu ve onun bir şey yapması gerekip gerekmediğini söyle (çoğu zaman gerekmez).
