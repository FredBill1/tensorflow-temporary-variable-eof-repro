"""Minimal CPU reproduction of Grappler TemporaryVariable/EOF collision."""

import argparse
import time

import tensorflow as tf

TASKS = 2
BATCH_SIZE = 32


class DirectSumLoss(tf.keras.losses.Loss):
    def __init__(self, seed, use_stack):
        super().__init__(name="DirectSumLoss")
        self.seed = seed
        self.use_stack = use_stack
        self.focal = tf.keras.losses.BinaryFocalCrossentropy()

    def call(self, y_true, y_pred):
        first = self.seed.read_value()  # Independent of IteratorGetNext.
        deps = []
        if y_true.shape[0] == BATCH_SIZE:
            # >80% of TF's 256 MiB CPU device memory estimate.
            with tf.control_dependencies([first]):
                deps.append(tf.raw_ops.Empty(shape=[55_000_000], dtype=tf.float32, init=True))
        with tf.control_dependencies(deps):
            terms = [self.focal(y_true[:, i : i + 1], y_pred[:, i : i + 1]) for i in range(TASKS)]
        inputs = [first, *terms]  # Three scalar inputs.
        if self.use_stack:
            return tf.reduce_sum(tf.stack(inputs))
        return tf.add_n(inputs)


def rows():
    for i in range(128):
        yield [i / 128], [(i + j) % 2 for j in range(TASKS)]
    time.sleep(0.5)  # Let the independent branch execute during EOF probe.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", action="store_true", help="use Pack+Sum instead of AddN (control)")
    parser.add_argument(
        "--known-cardinality", action="store_true", help="declare 4 batches to avoid EOF probing (control)"
    )
    args = parser.parse_args()

    # Explicit AddN reproduces even without ArithmeticOptimizer.
    tf.config.optimizer.set_experimental_options({"arithmetic_optimization": False})
    tf.keras.utils.set_random_seed(42)
    print("TensorFlow:", tf.__version__, "Keras:", tf.keras.Model.__module__, flush=True)

    train = tf.data.Dataset.from_generator(
        rows, output_signature=(tf.TensorSpec([1], tf.float32), tf.TensorSpec([TASKS], tf.float32))
    ).batch(BATCH_SIZE, drop_remainder=True)
    if args.known_cardinality:
        train = train.apply(tf.data.experimental.assert_cardinality(4))
    options = tf.data.Options()
    options.threading.private_threadpool_size = 2
    train = train.with_options(options)

    validation = tf.data.Dataset.from_tensors((tf.ones([16, 1]), tf.zeros([16, TASKS])))
    model = tf.keras.Sequential([tf.keras.Input(shape=(1,)), tf.keras.layers.Dense(TASKS, activation="sigmoid")])
    model.zero_seed = model.add_weight(name="zero_seed", shape=(), initializer="zeros", trainable=False)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3, clipnorm=1.0),
        loss=DirectSumLoss(model.zero_seed, args.stack),
        metrics=["binary_accuracy"],
        jit_compile=False,
    )
    print(
        "Cardinality:",
        int(tf.data.experimental.cardinality(train).numpy()),
        "sum:",
        "Pack+Sum" if args.stack else "AddN",
        flush=True,
    )
    model.fit(train, validation_data=validation, epochs=3, verbose=2)


if __name__ == "__main__":
    main()
