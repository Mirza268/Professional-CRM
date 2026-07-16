/* =============================================================================
   NEXUS CRM — 3D relationship network background
   A sparse cloud of nodes drifting in space, connecting when close together —
   a quiet visual echo of what a CRM actually does: link people and deals.
   Renders once and freezes for prefers-reduced-motion / no-WebGL fallback.
   ============================================================================= */
(function () {
  var canvasHost = document.getElementById('bg3d');
  if (!canvasHost || typeof THREE === 'undefined') return;

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.set(0, 0, 13);

  var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  canvasHost.appendChild(renderer.domElement);

  var group = new THREE.Group();
  scene.add(group);

  // ---- Nodes -----------------------------------------------------------
  var NODE_COUNT = window.innerWidth < 700 ? 34 : 60;
  var SPREAD = 9;
  var nodes = [];

  var nodeGeo = new THREE.SphereGeometry(0.045, 8, 8);
  var nodeMatAmber = new THREE.MeshBasicMaterial({ color: 0xf5a623 });
  var nodeMatCyan = new THREE.MeshBasicMaterial({ color: 0x22d3ee });

  for (var i = 0; i < NODE_COUNT; i++) {
    var mat = Math.random() > 0.82 ? nodeMatAmber : nodeMatCyan;
    var mesh = new THREE.Mesh(nodeGeo, mat);
    var pos = new THREE.Vector3(
      (Math.random() - 0.5) * SPREAD * 2,
      (Math.random() - 0.5) * SPREAD * 1.3,
      (Math.random() - 0.5) * SPREAD
    );
    mesh.position.copy(pos);
    mesh.userData.drift = new THREE.Vector3(
      (Math.random() - 0.5) * 0.0025,
      (Math.random() - 0.5) * 0.0025,
      (Math.random() - 0.5) * 0.0025
    );
    group.add(mesh);
    nodes.push(mesh);
  }

  // ---- Connections (lines between nearby nodes) -------------------------
  var lineMat = new THREE.LineBasicMaterial({ color: 0x3a4a6b, transparent: true, opacity: 0.35 });
  var lineGeo = new THREE.BufferGeometry();
  var MAX_DIST = 3.1;
  var linePositions = new Float32Array(NODE_COUNT * NODE_COUNT * 6);
  lineGeo.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
  var lines = new THREE.LineSegments(lineGeo, lineMat);
  group.add(lines);

  function updateLines() {
    var idx = 0;
    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var d = nodes[i].position.distanceTo(nodes[j].position);
        if (d < MAX_DIST) {
          linePositions[idx++] = nodes[i].position.x;
          linePositions[idx++] = nodes[i].position.y;
          linePositions[idx++] = nodes[i].position.z;
          linePositions[idx++] = nodes[j].position.x;
          linePositions[idx++] = nodes[j].position.y;
          linePositions[idx++] = nodes[j].position.z;
        }
      }
    }
    lineGeo.setDrawRange(0, idx / 3);
    lineGeo.attributes.position.needsUpdate = true;
  }

  updateLines();

  // ---- Resize -------------------------------------------------------------
  window.addEventListener('resize', function () {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // ---- Animate --------------------------------------------------------------
  var frame = 0;
  function animate() {
    frame++;
    group.rotation.y += 0.0009;
    group.rotation.x = Math.sin(frame * 0.0006) * 0.08;

    if (frame % 3 === 0) {
      nodes.forEach(function (n) {
        n.position.add(n.userData.drift);
        ['x', 'y', 'z'].forEach(function (axis) {
          if (Math.abs(n.position[axis]) > SPREAD) n.userData.drift[axis] *= -1;
        });
      });
      updateLines();
    }

    renderer.render(scene, camera);
    if (!reduceMotion) requestAnimationFrame(animate);
  }

  animate();
  if (reduceMotion) renderer.render(scene, camera); // single static frame
})();
