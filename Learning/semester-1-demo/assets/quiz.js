// Reusable retrieval-practice quiz.
// Markup: <div class="quiz"> containing one or more
//   <div class="q" data-answer="2" data-why="Explanation shown after answering">
//     <div class="q-prompt">Question?</div>
//     <div class="q-opts"><button>A</button><button>B</button>...</div>
//   </div>
// data-answer is the 0-based index of the correct button. The first click on a
// question locks it, marks the right answer, and shows the explanation.
(function () {
  function setup(quiz) {
    var qs = Array.prototype.slice.call(quiz.querySelectorAll('.q'));
    var score = document.createElement('p');
    score.className = 'q-score';
    quiz.appendChild(score);

    function update() {
      var done = qs.filter(function (q) { return q.classList.contains('done'); });
      var right = done.filter(function (q) { return q.dataset.correct === 'yes'; });
      score.innerHTML = done.length < qs.length
        ? done.length + ' of ' + qs.length + ' answered'
        : right.length + ' of ' + qs.length + ' correct. ' +
          '<button class="q-reset" type="button">Try again</button>';
      var reset = score.querySelector('.q-reset');
      if (reset) reset.addEventListener('click', function () { qs.forEach(clear); update(); });
    }

    function clear(q) {
      q.classList.remove('done');
      delete q.dataset.correct;
      q.querySelectorAll('button').forEach(function (b) {
        b.disabled = false; b.classList.remove('right', 'wrong');
      });
    }

    qs.forEach(function (q) {
      var answer = parseInt(q.dataset.answer, 10);
      var buttons = Array.prototype.slice.call(q.querySelectorAll('.q-opts button'));
      var why = document.createElement('p');
      why.className = 'q-why';
      why.textContent = q.dataset.why || '';
      q.appendChild(why);
      buttons.forEach(function (b, i) {
        b.type = 'button';
        b.addEventListener('click', function () {
          if (q.classList.contains('done')) return;
          q.classList.add('done');
          q.dataset.correct = i === answer ? 'yes' : 'no';
          buttons.forEach(function (x) { x.disabled = true; });
          buttons[answer].classList.add('right');
          if (i !== answer) b.classList.add('wrong');
          update();
        });
      });
    });
    update();
  }
  document.querySelectorAll('.quiz').forEach(setup);
})();
