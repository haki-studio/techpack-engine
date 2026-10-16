# Fonts used by projects/konpeito-jeans (OFL, Google Fonts). Downloads into the project inputs.
set -e
D="$(dirname "$0")/../projects/konpeito-jeans/inputs"
for f in zenmarugothic/ZenMaruGothic-Bold.ttf zenmarugothic/ZenMaruGothic-Medium.ttf yuseimagic/YuseiMagic-Regular.ttf \
         kiwimaru/KiwiMaru-Medium.ttf mochiypopone/MochiyPopOne-Regular.ttf hachimarupop/HachiMaruPop-Regular.ttf; do
  curl -sL "https://github.com/google/fonts/raw/main/ofl/$f" -o "$D/$(basename $f)"
done
cp "$D/ZenMaruGothic-Bold.ttf" "$D/zen.ttf"
