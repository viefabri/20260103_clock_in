# Streamlit JavaScriptハックによるショートカット実装の極意

StreamlitはPythonだけでWeb UIが作れる優れたフレームワークですが、**「任意のキーボードショートカットを実装する機能」は標準で存在しません**。
本プロジェクトでは、`st.components.v1.html` を利用してJavaScriptを注入し、高度なキーボード操作を実現しました。その技術的要点をまとめます。

## 1. 基本戦略: JavaScript Injection

Streamlitの `st.components.v1.html` を使うと、任意のHTML/JSをiframe内に描画できます。しかし、iframe内から外側（親ウィンドウ＝Streamlit本体）を操作するには `window.parent.document` へのアクセスが必要です。

```python
components.html(
    """
    <script>
    const doc = window.parent.document;
    // ここで親ウィンドウのDOMを操作する
    </script>
    """,
    height=0, width=0
)
```

## 2. 課題: Reactによる動的DOM生成

StreamlitのフロントエンドはReactで動いており、要素のIDやクラス名はハッシュ値が含まれたり、再レンダリングで頻繁に変わります（例: `css-1cpxqw2`）。
そのため、`getElementById` や固定のクラス名指定はすぐに壊れます。

### 対策: Attribute Injection パターン

「安定している情報（ラベルのテキストなど）」を頼りに要素を見つけ、**独自の安定したID (`data-testid`) を後から注入する** アプローチを取りました。

```javascript
// 例: "登録" というテキストを持つボタンを探して data-testid="btn-run" を付与
function assignIdByText(text, testId) {
    const xpath = `//button[contains(., '${text}')]`;
    // ... XPathで要素取得 ...
    el.setAttribute('data-testid', testId);
}
```

一度これを実行すれば、以降は `doc.querySelector('[data-testid="btn-run"]')` で確実にアクセスできます。

## 3. ロバスト性を高める実装テクニック

単純なテキスト一致では、「同じ単語を含む別の要素（コンテナdivなど）」を誤検知したり、大文字小文字の違いで失敗したりしました。以下の改良を行いました。

### A. Case-Insensitive XPath (大文字小文字無視)

XPath 1.0 では `lower-case()` が使えないため、`translate` 関数による置換テクニックを使用します。

```javascript
const lower = text.toLowerCase();
const translate = "translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')";
const xpath = `//${tagName}[contains(${translate}, '${lower}')]`;
```

### B. Proximity Search (近傍探索)

`<input>` タグ自体にはラベル情報がないことが多く、特定が困難です。
「Labelのテキスト」を見つけ、そこからDOMツリーを遡って近くにある `<input>` を探すロジックを実装しました。

```javascript
// ラベル要素を見つける
let label = ...;
// 親を遡りながら input を探す
let parent = label.parentElement;
while (parent) {
    const input = parent.querySelector('input');
    if (input) {
        input.setAttribute('data-testid', 'target-input-id');
        break;
    }
    parent = parent.parentElement;
}
```

### C. 誤検知の回避 (Heuristics)

`contains(., 'Time')` は、"Time" という文字を含む巨大な `<div>` 全体にもマッチしてしまいます。
これを除外するため、「テキストの長さが対象文字列 + 50文字以内」という条件を追加し、ピンポイントな要素のみ対象にしました。

## 4. 再レンダリングへの追従 (MutationObserver)

Streamlitは操作のたびにDOMを再構築します。一度IDを付与しても、画面更新で消えてしまいます。
`MutationObserver` を使い、DOMの変更を監視して、変更があるたびにID付与関数 (`assignTestIds`) を再実行させます。

```javascript
const observer = new MutationObserver(() => {
    assignTestIds();
});
observer.observe(doc.body, { childList: true, subtree: true });
```

## まとめ

Streamlitの制限を突破するには、**「DOM構造へのハッキング」** が不可欠ですが、以下の点に配慮することで実用的な堅牢性を確保できました。

1.  **Attribute Injection**: 不安定なDOMに自前のIDを振る。
2.  **Robust Matching**: 大文字小文字無視、近傍探索。
3.  **Persistence**: MutationObserverで再レンダリングに追従。

この手法は、Streamlitに限らず、IDが動的なWebアプリのスクレイピングや自動化（Selenium/Playwright）でも応用可能な汎用的なテクニックです。
