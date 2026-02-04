/**
 * HTML to PDF Converter using Playwright
 * Usage: node html-to-pdf.js [input.html] [output.pdf]
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function convertHtmlToPdf(inputPath, outputPath) {
    // デフォルトパスの設定
    const defaultInput = path.join(__dirname, '../プレイヤー配布用/index.html');
    const defaultOutput = path.join(__dirname, '../プレイヤー配布用/index.pdf');

    const htmlPath = inputPath || defaultInput;
    const pdfPath = outputPath || defaultOutput;

    // ファイル存在確認
    if (!fs.existsSync(htmlPath)) {
        console.error(`❌ ファイルが見つかりません: ${htmlPath}`);
        process.exit(1);
    }

    console.log('🚀 PDF変換を開始します...');
    console.log(`   入力: ${htmlPath}`);
    console.log(`   出力: ${pdfPath}`);

    const browser = await chromium.launch();

    try {
        const page = await browser.newPage();

        // ローカルHTMLファイルを開く
        const fileUrl = `file://${path.resolve(htmlPath)}`;
        await page.goto(fileUrl, { waitUntil: 'networkidle' });

        // PDFとして保存
        await page.pdf({
            path: pdfPath,
            format: 'A4',
            printBackground: true,
            margin: {
                top: '20mm',
                right: '15mm',
                bottom: '20mm',
                left: '15mm'
            }
        });

        console.log(`✅ PDF変換完了: ${pdfPath}`);

    } catch (error) {
        console.error('❌ エラーが発生しました:', error.message);
        process.exit(1);
    } finally {
        await browser.close();
    }
}

// コマンドライン引数を取得
const args = process.argv.slice(2);
convertHtmlToPdf(args[0], args[1]);
