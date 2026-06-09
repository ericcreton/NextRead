import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

function readRatings() {
  try {
    const value = JSON.parse(localStorage.getItem("nextread.ratings") || "{}");
    return Object.fromEntries(
      Object.entries(value).filter(
        ([id, r]) =>
          /^\d+$/.test(id) && Number.isInteger(r) && r >= 1 && r <= 5,
      ),
    );
  } catch {
    return {};
  }
}
async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok)
    throw new Error(
      "We couldn’t load your books. Check that the API is running and try again.",
    );
  return response.json();
}
function App() {
  const [ratings, setRatings] = useState(readRatings),
    [diverse, setDiverse] = useState(true),
    [query, setQuery] = useState(""),
    [books, setBooks] = useState([]),
    [total, setTotal] = useState(0),
    [page, setPage] = useState(0),
    [tab, setTab] = useState("discover"),
    [result, setResult] = useState(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [retry, setRetry] = useState(0);
  const count = Object.keys(ratings).length;
  useEffect(() => {
    try {
      localStorage.setItem("nextread.ratings", JSON.stringify(ratings));
    } catch {}
  }, [ratings]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const timer = setTimeout(async () => {
      try {
        const data = await api(
          `/api/books?q=${encodeURIComponent(query)}&offset=${page * 24}`,
        );
        if (active) {
          setBooks(data.books);
          setTotal(data.total);
        }
      } catch (e) {
        if (active) setError(e.message);
      } finally {
        if (active) setLoading(false);
      }
    }, 200);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query, page, retry]);
  useEffect(() => {
    let active = true;
    setResult(null);
    api("/api/recommendations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        diverse,
        ratings: Object.entries(ratings).map(([id, rating]) => ({
          book_id: Number(id),
          rating,
        })),
      }),
    })
      .then((data) => {
        if (active) setResult(data);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [ratings, retry, diverse]);
  function rate(id, value) {
    setRatings((old) => {
      const next = { ...old };
      if (next[id] === value) delete next[id];
      else next[id] = value;
      return next;
    });
  }
  const visible = tab === "discover" ? books : result?.books || [];
  return (
    <>
      <header>
        <a className="brand" href="/">
          n<span>↗</span> <b>NextRead</b>
        </a>
        <span className="edition">
          A little curiosity. A great next chapter.
        </span>
        <div className="avatar">You</div>
      </header>
      <main>
        <section className="hero">
          <div>
            <div className="eyebrow">FOR THE LOVE OF THE NEXT BOOK</div>
            <h1>
              Your next chapter
              <br />
              starts with <em>you.</em>
            </h1>
            <p>
              Old favorites. New worlds. Rate the books you know,
              <br className="desktop" /> and discover the ones you’ll want to
              get lost in.
            </p>
            <button
              className="primary"
              onClick={() =>
                document
                  .getElementById("catalog")
                  .scrollIntoView({ behavior: "smooth" })
              }
            >
              Build your reading profile <span>↗</span>
            </button>
            <div className="hero-note">
              10,000 books. One very personal reading list.
            </div>
          </div>
          <div className="book-art" aria-hidden="true">
            <div className="art-book one">
              <small>J. R. R. TOLKIEN</small>
              <strong>
                THE
                <br />
                HOBBIT
              </strong>
              <span>☼</span>
              <small>THERE AND BACK AGAIN</small>
            </div>
            <div className="art-book two">
              <small>JANE AUSTEN</small>
              <strong>
                Pride
                <br />
                <i>and</i>
                <br />
                Prejudice
              </strong>
              <span>❦</span>
            </div>
            <div className="art-label">
              There’s a whole world
              <br />
              on your next shelf.
            </div>
          </div>
        </section>
        <div className="workspace" id="catalog">
          <section className="catalog">
            <div className="section-head">
              <div>
                <div className="eyebrow">THE DISCOVERY SHELF</div>
                <h2>
                  {tab === "discover"
                    ? "Start with a few familiar faces."
                    : "A new chapter, picked for you."}
                </h2>
              </div>
              <span className="catalog-count">
                {total.toLocaleString()} books
              </span>
            </div>
            <div className="toolbar">
              <div className="tabs">
                <button
                  className={tab === "discover" ? "active" : ""}
                  onClick={() => setTab("discover")}
                >
                  Explore books
                </button>
                <button
                  className={tab === "picks" ? "active" : ""}
                  onClick={() => setTab("picks")}
                >
                  Your next reads <span>↗</span>
                </button>
              </div>
              {tab === "picks" && (
                <label className="discovery-toggle">
                  <input type="checkbox" checked={diverse} onChange={e => setDiverse(e.target.checked)} />
                  More variety
                </label>
              )}
              {tab === "discover" && (
                <input
                  aria-label="Search books or authors"
                  placeholder="Search a title or author…"
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setPage(0);
                  }}
                />
              )}
            </div>
            {tab === "picks" && diverse && <p className="ranking-note">Up to two books per author, one per series, and fewer boxed sets.</p>}
            {error ? (
              <div className="empty" role="alert">
                {error}{" "}
                <button onClick={() => setRetry(retry + 1)}>Try again</button>
              </div>
            ) : (tab === "discover" ? loading : !result) ? (
              <p className="empty" role="status">
                Finding your next chapter…
              </p>
            ) : visible.length === 0 ? (
              <p className="empty">
                {query
                  ? "No books found. Try another title or author."
                  : "Your shelf is empty. Import the Goodbooks catalog to get started."}
              </p>
            ) : (
              <div className="grid">
                {visible.map((book) => (
                  <article className="book-card" key={book.id}>
                    <div className={"cover tone-" + (book.id % 6)}>
                      <small>{book.authors.split(",")[0]}</small>
                      <strong>{book.title.split(" (")[0]}</strong>
                      <span className="cover-symbol">
                        {["✳", "❦", "◈", "☾", "✺", "◇"][book.id % 6]}
                      </span>
                      <small>
                        {book.genres[0]?.replaceAll("-", " ") ||
                          "THE READING COLLECTION"}
                      </small>
                    </div>
                    <h3 title={book.title}>{book.title}</h3>
                    <p className="author">{book.authors}</p>
                    <div className="community">
                      ★ {book.average_rating.toFixed(2)}{" "}
                      <span>community rating</span>
                    </div>
                    {tab === "picks" && <p className="reason">{book.reason}</p>}
                    <div className="stars" aria-label={`Rate ${book.title}`}>
                      {[1, 2, 3, 4, 5].map((value) => (
                        <button
                          key={value}
                          aria-label={`${value} star${value === 1 ? "" : "s"} for ${book.title}`}
                          aria-pressed={ratings[book.id] === value}
                          className={
                            (ratings[book.id] || 0) >= value ? "selected" : ""
                          }
                          onClick={() => rate(book.id, value)}
                        >
                          ★
                        </button>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            )}
            {tab === "discover" && total > 24 && (
              <div className="pagination">
                <button disabled={page === 0} onClick={() => setPage(page - 1)}>
                  ← Previous
                </button>
                <span>
                  Page {page + 1} of {Math.ceil(total / 24)}
                </span>
                <button
                  disabled={(page + 1) * 24 >= total}
                  onClick={() => setPage(page + 1)}
                >
                  Next →
                </button>
              </div>
            )}
          </section>
          <aside>
            <div className="profile-icon">✳</div>
            <div className="eyebrow">A SHELF THAT FEELS LIKE YOU</div>
            <h2>Your reading profile</h2>
            <p>Every rating tells us a little more about your kind of story.</p>
            <div className="progress-label">
              <b>
                {count} {count === 1 ? "book" : "books"} rated
              </b>
              <span>{Math.min(count, 10)} / 10</span>
            </div>
            <div className="progress">
              <span style={{ width: Math.min(count * 10, 100) + "%" }} />
            </div>
            <p className="hint">
              {count < 10
                ? `Rate ${10 - count} more to round out your profile.`
                : "A lovely start. Keep rating to refine your picks."}
            </p>
            <hr />
            {result?.profile.length > 0 ? (
              <>
                <h4>Your favorite shelves</h4>
                {result.profile.map((p) => (
                  <div className="genre" key={p.genre}>
                    <div>
                      <span>{p.genre.replaceAll("-", " ")}</span>
                    </div>
                    <div className="progress">
                      <span style={{ width: p.strength + "%" }} />
                    </div>
                  </div>
                ))}
                <p className="hint">
                  Relative genre affinity from your ratings, not a probability.
                </p>
              </>
            ) : (
              <div className="profile-empty">
                Your taste will take shape here.
                <br />
                Give a favorite book its first stars.
              </div>
            )}
            <button
              className="primary profile-cta"
              onClick={() => setTab("picks")}
            >
              {count ? "Find my next read" : "Explore reader favorites"}{" "}
              <span>→</span>
            </button>
            <div className="method">
              {result?.method === "hybrid-svd"
                  ? "Powered by trained collaborative filtering, genres & authors."
                  : result?.method === "content-popularity"
                ? "Based on genres, authors & community ratings."
                : "Start with community favorites."}
            </div>
            {count > 0 && (
              <button className="reset" onClick={() => setRatings({})}>
                Clear my ratings
              </button>
            )}
          </aside>
        </div>
        <footer>
          <span className="brand">NextRead</span>
          <span>Made for curious readers. Powered by Goodbooks-10k.</span>
          <a href="https://github.com/zygmuntz/goodbooks-10k">
            About the dataset ↗
          </a>
        </footer>
      </main>
    </>
  );
}
createRoot(document.getElementById("root")).render(<App />);
