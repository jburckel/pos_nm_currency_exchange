/* Rate board of the exchange counter: clock, and rates reloaded from the
   JSON route every data-refresh seconds. The last rates stay on screen
   while the server cannot be reached. No Odoo assets: plain DOM. */
(function () {
    "use strict";
    const body = document.body;
    const url = body.dataset.url;
    const refresh = Math.max(10, parseInt(body.dataset.refresh, 10) || 60) * 1000;
    const lang = document.documentElement.lang || undefined;

    function tick() {
        const time = document.getElementById("nm-board-time");
        if (time) {
            time.textContent = new Date().toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" });
        }
    }

    function cell(tag, className, parts) {
        const element = document.createElement(tag);
        if (className) {
            element.className = className;
        }
        for (const part of parts) {
            element.append(part);
        }
        return element;
    }

    function small(text) {
        return cell("small", "", [text]);
    }

    function render(board) {
        const rows = document.getElementById("nm-board-rows");
        const commissions = document.getElementById("nm-board-commissions");
        rows.replaceChildren(
            ...board.rows.map((row) =>
                cell("tr", "", [
                    cell("td", "nm-col-currency", [cell("span", "nm-code", [row.currency])]),
                    cell("td", "nm-col-rate", [row.buy_rate_label]),
                    cell("td", "nm-col-rate", [row.sell_rate_label]),
                    cell("td", "nm-col-amount", [
                        small(row.amount_formatted),
                        document.createElement("br"),
                        row.buy_amount_formatted,
                    ]),
                    cell("td", "nm-col-amount", [
                        small(row.amount_formatted),
                        document.createElement("br"),
                        row.sell_amount_formatted,
                    ]),
                ])
            )
        );
        commissions.replaceChildren(
            ...board.rows.map((row) =>
                cell("li", "", [cell("strong", "", [row.currency]), ": " + row.commission_label])
            )
        );
        document.getElementById("nm-board-date").textContent = board.date;
    }

    async function reload() {
        const offline = document.getElementById("nm-board-offline");
        try {
            const response = await fetch(url, { cache: "no-store", credentials: "omit" });
            if (!response.ok) {
                throw new Error(String(response.status));
            }
            render(await response.json());
            offline.hidden = true;
        } catch {
            offline.hidden = false;
        }
    }

    tick();
    setInterval(tick, 15000);
    if (url) {
        setInterval(reload, refresh);
    }
})();
