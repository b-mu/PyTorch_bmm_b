#include <torch/extension.h>

#include <cuda.h>
#include <cuda_runtime.h>

#include <vector>

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include <string.h> //for memcpy

#include <magma_v2.h>

// Pulled from magma test code
#define TESTING_CHECK( err )                                                 \
    do {                                                                     \
        magma_int_t err_ = (err);                                            \
        if ( err_ != 0 ) {                                                   \
            fprintf( stderr, "Error: %s\nfailed at %s:%d: error %lld: %s\n", \
                     #err, __FILE__, __LINE__,                               \
                     (long long) err_, magma_strerror(err_) );               \
            exit(1);                                                         \
        }                                                                    \
    } while( 0 )

namespace {


// template <typename scalar_t>
// __global__ void bmm_cuda_forward_kernel(
//     const torch::PackedTensorAccessor<scalar_t,3,torch::RestrictPtrTraits,size_t> gates,
//     const torch::PackedTensorAccessor<scalar_t,2,torch::RestrictPtrTraits,size_t> old_cell,
//     torch::PackedTensorAccessor<scalar_t,2,torch::RestrictPtrTraits,size_t> new_h,
//     torch::PackedTensorAccessor<scalar_t,2,torch::RestrictPtrTraits,size_t> new_cell,
//     torch::PackedTensorAccessor<scalar_t,2,torch::RestrictPtrTraits,size_t> input_gate,
//     torch::PackedTensorAccessor<scalar_t,2,torch::RestrictPtrTraits,size_t> output_gate,
//     torch::PackedTensorAccessor<scalar_t,2,torch::RestrictPtrTraits,size_t> candidate_cell) {
//   //batch index
//   const int n = blockIdx.y;
//   // column index
//   const int c = blockIdx.x * blockDim.x + threadIdx.x;
//   if (c < gates.size(2)){
//     input_gate[n][c] = sigmoid(gates[n][0][c]);
//     output_gate[n][c] = sigmoid(gates[n][1][c]);
//     candidate_cell[n][c] = elu(gates[n][2][c]);
//     new_cell[n][c] =
//         old_cell[n][c] + candidate_cell[n][c] * input_gate[n][c];
//     new_h[n][c] = tanh(new_cell[n][c]) * output_gate[n][c];
//   }
// }


} // namespace

int bmm_cuda_forward(
    std::vector<torch::Tensor> A,
    std::vector<torch::Tensor> B,
    std::vector<torch::Tensor> C,
    int* m,
    int* n,
    int* k) {
  // auto X = torch::cat({old_h, input}, /*dim=*/1);
  // auto gate_weights = torch::addmm(bias, X, weights.transpose(0, 1));

  // const auto batch_size = old_cell.size(0);
  // const auto state_size = old_cell.size(1);

  // auto gates = gate_weights.reshape({batch_size, 3, state_size});
  // auto new_h = torch::zeros_like(old_cell);
  // auto new_cell = torch::zeros_like(old_cell);
  // auto input_gate = torch::zeros_like(old_cell);
  // auto output_gate = torch::zeros_like(old_cell);
  // auto candidate_cell = torch::zeros_like(old_cell);

  // const int threads = 1024;
  // const dim3 blocks((state_size + threads - 1) / threads, batch_size);

  // AT_DISPATCH_FLOATING_TYPES(gates.type(), "lltm_forward_cuda", ([&] {
  //   lltm_cuda_forward_kernel<scalar_t><<<blocks, threads>>>(
  //       gates.packed_accessor<scalar_t,3,torch::RestrictPtrTraits,size_t>(),
  //       old_cell.packed_accessor<scalar_t,2,torch::RestrictPtrTraits,size_t>(),
  //       new_h.packed_accessor<scalar_t,2,torch::RestrictPtrTraits,size_t>(),
  //       new_cell.packed_accessor<scalar_t,2,torch::RestrictPtrTraits,size_t>(),
  //       input_gate.packed_accessor<scalar_t,2,torch::RestrictPtrTraits,size_t>(),
  //       output_gate.packed_accessor<scalar_t,2,torch::RestrictPtrTraits,size_t>(),
  //       candidate_cell.packed_accessor<scalar_t,2,torch::RestrictPtrTraits,size_t>());
  // }));

  double ** hA_array;
  double ** hB_array;
  double ** hC_array;

  double const* * dA_array;
  double const* * dB_array;
  double **dC_array;

  magma_int_t* d_m;
  magma_int_t* d_n;
  magma_int_t* d_k;

  double  alpha = 1.0;
  double  beta = 0.0;
  magma_int_t* d_lddb;
  magma_int_t* d_ldda;
  magma_int_t* d_lddc;



  magma_trans_t transA = MagmaNoTrans;
  magma_trans_t transB = MagmaNoTrans;

  magma_int_t batchCount = 2;
  magma_queue_t queue;


  TESTING_CHECK( magma_malloc_cpu( (void**)&hA_array, sizeof(double*)*batchCount ) );
  TESTING_CHECK( magma_malloc_cpu( (void**)&hB_array, sizeof(double*)*batchCount ) );
  TESTING_CHECK( magma_malloc_cpu( (void**)&hC_array, sizeof(double*)*batchCount ) );

  TESTING_CHECK( magma_malloc((void**)&d_m, (batchCount+1)*sizeof(magma_int_t)) );
  TESTING_CHECK( magma_malloc((void**)&d_n, (batchCount+1)*sizeof(magma_int_t)) );
  TESTING_CHECK( magma_malloc((void**)&d_k, (batchCount+1)*sizeof(magma_int_t)) );

  TESTING_CHECK( magma_malloc((void**)&d_ldda, (batchCount+1)*sizeof(magma_int_t) ) );
  TESTING_CHECK( magma_malloc((void**)&d_lddb, (batchCount+1)*sizeof(magma_int_t) ) );
  TESTING_CHECK( magma_malloc((void**)&d_lddc, (batchCount+1)*sizeof(magma_int_t) ) );

  for (int i = 0; i < batchCount; ++i)
  {
    hA_array[i] = (double *) A[i].data_ptr();
    hB_array[i] = (double *) B[i].data_ptr();
    hC_array[i] = (double *) C[i].data_ptr();
  }



  // dA_array is the array of pointers need by dgemm
  // d_A_elems are the actual mtx elements being pointed to
  // hA_array is the host side pointers that will get passed to dA_array
  // double const* * dA_array;
  // double const* * dB_array;
  // double ** dC_array;

  TESTING_CHECK( magma_malloc( (void**)&dA_array, sizeof(double*)*batchCount ) );
  TESTING_CHECK( magma_malloc( (void**)&dB_array, sizeof(double*)*batchCount ) );
  TESTING_CHECK( magma_malloc( (void**)&dC_array, sizeof(double*)*batchCount ) );

  magma_setvector(batchCount, sizeof(double*), hA_array, 1, dA_array, 1, queue);
  magma_setvector(batchCount, sizeof(double*), hB_array, 1, dB_array, 1, queue);
  magma_setvector(batchCount, sizeof(double*), hC_array, 1, dC_array, 1, queue);


  magma_setvector(batchCount, sizeof(magma_int_t), m, 1, d_m, 1, queue);
  magma_setvector(batchCount, sizeof(magma_int_t), n, 1, d_n, 1, queue);
  magma_setvector(batchCount, sizeof(magma_int_t), k, 1, d_k, 1, queue);
  magma_setvector(batchCount, sizeof(magma_int_t), m, 1, d_ldda, 1, queue);
  magma_setvector(batchCount, sizeof(magma_int_t), k, 1, d_lddb, 1, queue);
  magma_setvector(batchCount, sizeof(magma_int_t), m, 1, d_lddc, 1, queue);

  // TESTING_CHECK( magma_malloc((void**)&d_m, (batchCount+1)*sizeof(magma_int_t)) );
  // TESTING_CHECK( magma_malloc((void**)&d_n, (batchCount+1)*sizeof(magma_int_t)) );
  // TESTING_CHECK( magma_malloc((void**)&d_k, (batchCount+1)*sizeof(magma_int_t)) );


  magmablas_dgemm_vbatched(       transA,
      /* magma_trans_t */         transB,
      /* magma_int_t * */         d_m,
      /* magma_int_t * */         d_n,
      /* magma_int_t * */         d_k,
      /* double */                alpha,
      /* double const *const * */ dA_array,
      /* magma_int_t * */         d_ldda,
      /* double const *const * */ dB_array,
      /* magma_int_t * */         d_lddb,
      /* double */                beta,
      /* double ** */             dC_array,
      /* magma_int_t * */         d_lddc,
      /* magma_int_t */           batchCount,
      /* magma_queue_t */         queue);

  return 2;
}
