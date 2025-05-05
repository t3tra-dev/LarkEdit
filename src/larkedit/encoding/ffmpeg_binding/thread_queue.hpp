#pragma once
#include <condition_variable>
#include <mutex>
#include <queue>
#include <optional>

template <typename T>
class ThreadQueue {
public:
    explicit ThreadQueue(size_t cap = 16) : _cap(cap) {}
    void push(T v) {
        std::unique_lock lk(_mtx);
        _cv_full.wait(lk, [&]{ return _q.size() < _cap || _closed; });
        if (_closed) return;
        _q.push(std::move(v));
        _cv_empty.notify_one();
    }
    std::optional<T> pop() {
        std::unique_lock lk(_mtx);
        _cv_empty.wait(lk, [&]{ return !_q.empty() || _closed; });
        if (_q.empty()) return std::nullopt;
        T v = std::move(_q.front()); _q.pop();
        _cv_full.notify_one();
        return v;
    }
    void close() {
        { std::scoped_lock lk(_mtx); _closed = true; }
        _cv_empty.notify_all(); _cv_full.notify_all();
    }
private:
    std::mutex _mtx;
    std::condition_variable _cv_empty, _cv_full;
    std::queue<T> _q;
    size_t _cap;
    bool _closed{false};
};
